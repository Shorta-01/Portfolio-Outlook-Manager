import logging
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetMode, AssetType
from app.providers.fallback_provider import FallbackProvider
from app.providers.manual_provider import ManualProvider
from app.providers.symbol_resolver import SymbolResolver
from app.providers.twelve_data_provider import TwelveDataProvider
from app.repositories.asset_repo import AssetRepository
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.market_data_ingestion_service import MarketDataIngestionService
from app.services.scheduler_state import scheduler_state
from app.services.valuation_service import MARKET_PRICED_TYPES

logger = logging.getLogger(__name__)


@dataclass
class BackfillResult:
    started: bool
    completed: bool
    success: bool
    rows_inserted_quotes: int
    rows_inserted_fx: int
    lookup_possible: bool
    lookup_reason: str
    provider_used: str | None
    error_type: str | None
    error_message: str | None
    user_message: str
    outcome: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["ok"] = self.success
        payload["quotes"] = self.rows_inserted_quotes
        payload["fx"] = self.rows_inserted_fx
        return payload


class HistoryService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.lot_repo = LotRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.manual_provider = ManualProvider(MarketQuoteRepository(db), FXRateRepository(db))
        self.twelve_data_provider = TwelveDataProvider()
        self.provider = FallbackProvider([self.twelve_data_provider, self.manual_provider])
        self.ingestion = MarketDataIngestionService(db)
        self.resolver = SymbolResolver()

    def backfill_asset(self, asset: Asset) -> dict:
        logger.info("Backfill requested asset_id=%s type=%s mode=%s", asset.id, asset.asset_type.value, asset.asset_mode.value)

        if asset.asset_type in {AssetType.CASH, AssetType.TERM_DEPOSIT} or asset.asset_type not in MARKET_PRICED_TYPES:
            result = self._result(
                success=False,
                started=False,
                outcome="skipped_not_market_priced",
                lookup_possible=False,
                lookup_reason="Backfill skipped: asset is not market-priced",
                error_type="not_market_priced",
                error_message="Backfill disabled for non-market-priced assets",
                user_message="Backfill skipped: asset is not market-priced.",
            )
            logger.info("Backfill final outcome asset_id=%s outcome=%s", asset.id, result["outcome"])
            return result

        resolved = self.resolver.resolve(asset)
        logger.info(
            "Backfill symbol resolution asset_id=%s lookup_possible=%s provider=%s symbol=%s reason=%s",
            asset.id,
            resolved.lookup_possible,
            resolved.provider_name,
            resolved.provider_symbol,
            resolved.lookup_reason,
        )
        if not resolved.lookup_possible:
            result = self._result(
                success=False,
                started=False,
                outcome="skipped_lookup_impossible",
                lookup_possible=False,
                lookup_reason=resolved.lookup_reason,
                provider_used=resolved.provider_name,
                error_type="lookup_impossible",
                error_message=resolved.lookup_reason,
                user_message=f"Backfill skipped: asset is not externally resolvable ({resolved.lookup_reason}).",
            )
            logger.info("Backfill final outcome asset_id=%s outcome=%s", asset.id, result["outcome"])
            return result

        provider_name = resolved.provider_name or "fallback"
        if (
            provider_name == "twelve_data"
            and isinstance(self.provider, FallbackProvider)
            and self.twelve_data_provider in self.provider.providers
            and not self.twelve_data_provider.api_key
        ):
            result = self._result(
                success=False,
                started=False,
                outcome="failed_provider_not_configured",
                lookup_possible=True,
                lookup_reason=resolved.lookup_reason,
                provider_used=provider_name,
                error_type="provider_not_configured",
                error_message="TWELVE_DATA_API_KEY is not configured",
                user_message="Backfill failed: market data provider is not configured.",
            )
            logger.warning("Backfill provider not configured asset_id=%s provider=%s", asset.id, provider_name)
            logger.info("Backfill final outcome asset_id=%s outcome=%s", asset.id, result["outcome"])
            return result

        settings = self.settings_repo.get_first()
        years = settings.backfill_daily_years_default if settings else 5
        end_date = date.today()
        if asset.asset_mode == AssetMode.OWNED:
            lots = self.lot_repo.list_for_asset(asset.id)
            earliest_lot = min((lot.buy_date for lot in lots), default=end_date)
            start_date = earliest_lot - timedelta(days=365 * years)
        else:
            start_date = end_date - timedelta(days=365 * years)

        provider = self._provider_for_resolution(resolved.provider_name)
        logger.info("Backfill provider selected asset_id=%s provider=%s", asset.id, provider_name)
        try:
            logger.info("Backfill provider call started asset_id=%s provider=%s", asset.id, provider_name)
            history = provider.fetch_historical_daily(asset, start_date, end_date)
            logger.info("Backfill provider returned quote_rows=%s asset_id=%s", len(history), asset.id)
        except Exception as exc:  # noqa: BLE001
            scheduler_state.mark_job_failure("backfill", str(exc))
            self.db.rollback()
            logger.exception("Backfill provider error asset_id=%s provider=%s", asset.id, provider_name)
            return self._result(
                success=False,
                started=True,
                outcome="failed_provider_error",
                lookup_possible=True,
                lookup_reason=resolved.lookup_reason,
                provider_used=provider_name,
                error_type="provider_error",
                error_message=str(exc),
                user_message="Backfill failed: provider returned error.",
            )

        try:
            quote_count = 0
            for item in history:
                self.ingestion.ingest_quote(asset.id, item, is_backfill=True)
                quote_count += 1

            fx_count = 0
            base_currency = (settings.portfolio_base_currency if settings else "EUR").upper()
            if asset.quote_currency.upper() != base_currency:
                fx_rows = provider.fetch_historical_fx(asset.quote_currency.upper(), base_currency, start_date, end_date)
                logger.info("Backfill FX provider returned rows=%s asset_id=%s", len(fx_rows), asset.id)
                for fx in fx_rows:
                    self.ingestion.ingest_fx(fx)
                    fx_count += 1

            scheduler_state.mark_job_success("backfill")
            self.db.commit()
            result = self._result(
                success=True,
                started=True,
                outcome="completed_with_data" if quote_count else "completed_no_data",
                lookup_possible=True,
                lookup_reason=resolved.lookup_reason,
                provider_used=provider_name,
                rows_inserted_quotes=quote_count,
                rows_inserted_fx=fx_count,
                user_message=(
                    f"Backfill completed: {quote_count} quote rows loaded."
                    if quote_count
                    else "Backfill completed, but no data was found for this asset."
                ),
            )
            logger.info(
                "Backfill rows inserted asset_id=%s quote_rows=%s fx_rows=%s",
                asset.id,
                quote_count,
                fx_count,
            )
            logger.info("Backfill final outcome asset_id=%s outcome=%s", asset.id, result["outcome"])
            return result
        except Exception as exc:  # noqa: BLE001
            scheduler_state.mark_job_failure("backfill", str(exc))
            self.db.rollback()
            logger.exception("Backfill failed with unexpected exception asset_id=%s", asset.id)
            return self._result(
                success=False,
                started=True,
                outcome="failed_unexpected_exception",
                lookup_possible=True,
                lookup_reason=resolved.lookup_reason,
                provider_used=provider_name,
                error_type="unexpected_exception",
                error_message=str(exc),
                user_message="Backfill failed: unexpected exception.",
            )

    def backfill_asset_by_id(self, asset_id: int) -> dict:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            return self._result(
                success=False,
                started=False,
                outcome="failed_asset_not_found",
                lookup_possible=False,
                lookup_reason="Asset not found",
                error_type="asset_not_found",
                error_message="Asset not found",
                user_message="Backfill failed: asset not found.",
            )
        return self.backfill_asset(asset)

    def _provider_for_resolution(self, provider_name: str | None):
        return self.provider

    def _result(
        self,
        *,
        success: bool,
        started: bool,
        outcome: str,
        lookup_possible: bool,
        lookup_reason: str,
        provider_used: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        user_message: str,
        rows_inserted_quotes: int = 0,
        rows_inserted_fx: int = 0,
    ) -> dict:
        return BackfillResult(
            started=started,
            completed=True,
            success=success,
            rows_inserted_quotes=rows_inserted_quotes,
            rows_inserted_fx=rows_inserted_fx,
            lookup_possible=lookup_possible,
            lookup_reason=lookup_reason,
            provider_used=provider_used,
            error_type=error_type,
            error_message=error_message,
            user_message=user_message,
            outcome=outcome,
        ).to_dict()
