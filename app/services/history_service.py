from datetime import date, datetime, timedelta

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


class HistoryService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.lot_repo = LotRepository(db)
        self.settings_repo = SettingsRepository(db)
        manual = ManualProvider(MarketQuoteRepository(db), FXRateRepository(db))
        self.provider = FallbackProvider([TwelveDataProvider(), manual])
        self.ingestion = MarketDataIngestionService(db)
        self.resolver = SymbolResolver()

    def backfill_asset(self, asset: Asset) -> dict:
        if asset.asset_type in {AssetType.CASH, AssetType.TERM_DEPOSIT}:
            return {"ok": False, "reason": "Backfill disabled for cash/term deposits", "quotes": 0, "fx": 0}
        if asset.asset_type not in MARKET_PRICED_TYPES:
            return {"ok": False, "reason": "Asset type not market-priced", "quotes": 0, "fx": 0}

        resolved = self.resolver.resolve(asset)
        if not resolved.lookup_possible:
            return {"ok": False, "reason": resolved.lookup_reason, "quotes": 0, "fx": 0}

        settings = self.settings_repo.get_first()
        years = settings.backfill_daily_years_default if settings else 5
        end_date = date.today()
        if asset.asset_mode == AssetMode.OWNED:
            lots = self.lot_repo.list_for_asset(asset.id)
            earliest_lot = min((lot.buy_date for lot in lots), default=end_date)
            start_date = earliest_lot - timedelta(days=365 * years)
        else:
            start_date = end_date - timedelta(days=365 * years)

        history = self.provider.fetch_historical_daily(asset, start_date, end_date)
        quote_count = 0
        for item in history:
            self.ingestion.ingest_quote(asset.id, item, is_backfill=True)
            quote_count += 1

        fx_count = 0
        base_currency = (settings.portfolio_base_currency if settings else "EUR").upper()
        if asset.quote_currency.upper() != base_currency:
            fx_rows = self.provider.fetch_historical_fx(asset.quote_currency.upper(), base_currency, start_date, end_date)
            for fx in fx_rows:
                self.ingestion.ingest_fx(fx)
                fx_count += 1

        scheduler_state.last_successful_backfill_utc = datetime.utcnow()
        self.db.commit()
        return {"ok": True, "reason": "backfill completed", "quotes": quote_count, "fx": fx_count}

    def backfill_asset_by_id(self, asset_id: int) -> dict:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            return {"ok": False, "reason": "Asset not found", "quotes": 0, "fx": 0}
        return self.backfill_asset(asset)
