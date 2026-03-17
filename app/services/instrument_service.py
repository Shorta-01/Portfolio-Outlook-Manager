from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetMode, AssetType
from app.models.polling_rule import PollingRule
from app.repositories.asset_repo import AssetRepository
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.asset import AssetCreate
from app.schemas.asset import AssetUpdate
from app.services.asset_identity_service import AssetIdentityService
from app.services.history_service import HistoryService

POLL_CAPABLE_TYPES = {
    AssetType.STOCK,
    AssetType.ETF,
    AssetType.FUND,
    AssetType.GOLD,
    AssetType.OIL,
    AssetType.BOND,
    AssetType.FOREX,
    AssetType.CRYPTO,
    AssetType.OTHER,
}


class InstrumentService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.polling_repo = PollingRuleRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.identity_service = AssetIdentityService()

    def create_asset(self, payload: AssetCreate) -> Asset:
        asset, _ = self.create_or_reuse_asset(payload)
        return asset

    def trigger_backfill(self, asset_id: int) -> dict:
        return HistoryService(self.db).backfill_asset_by_id(asset_id)

    def create_or_reuse_asset(self, payload: AssetCreate) -> tuple[Asset, bool]:
        existing = self.find_by_identity(payload)
        if existing is not None:
            return existing, False

        asset = Asset(
            symbol_internal=f"asset_{uuid4().hex[:12]}",
            display_name=payload.display_name.strip(),
            asset_type=payload.asset_type,
            asset_mode=payload.asset_mode,
            quote_currency=payload.quote_currency.upper(),
            exchange=payload.exchange,
            isin=(payload.isin.strip().upper() if payload.isin else None),
            is_manual_asset=payload.is_manual_asset,
            current_amount=payload.current_amount,
            principal_amount=payload.principal_amount,
            interest_rate_annual=payload.interest_rate_annual,
            start_date=payload.start_date,
            maturity_date=payload.maturity_date,
            accrual_method=payload.accrual_method,
            payout_type=payload.payout_type,
            bank_name=payload.bank_name,
        )
        self.asset_repo.add(asset)
        self._create_default_polling_rule(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset, True

    def find_by_identity(self, payload: AssetCreate) -> Asset | None:
        identity_key = self.identity_service.key_for_create(payload)
        for asset in self.asset_repo.list_all():
            if self.identity_service.key_for_asset(asset) == identity_key:
                return asset
        return None


    def promote_watchlist_to_owned(self, asset_id: int) -> Asset:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise ValueError("Asset not found")
        if asset.asset_mode != AssetMode.WATCHLIST:
            raise ValueError("Only watchlist assets can be promoted")
        asset.asset_mode = AssetMode.OWNED
        self._create_default_polling_rule(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def update_asset(self, asset_id: int, payload: AssetUpdate) -> Asset:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise ValueError("Asset not found")

        asset.display_name = payload.display_name.strip()
        asset.quote_currency = payload.quote_currency.strip().upper()
        asset.exchange = payload.exchange
        asset.isin = payload.isin.strip().upper() if payload.isin else None
        asset.provider_symbol_primary = payload.provider_symbol_primary.strip().upper() if payload.provider_symbol_primary else None

        is_cash = asset.asset_mode == AssetMode.CASH or asset.asset_type == AssetType.CASH
        if is_cash:
            if payload.current_amount is None:
                raise ValueError("Cash assets require current amount")
            asset.current_amount = payload.current_amount

        is_td = asset.asset_mode == AssetMode.TERM_DEPOSIT or asset.asset_type == AssetType.TERM_DEPOSIT
        if is_td:
            if payload.principal_amount is None or payload.interest_rate_annual is None or payload.start_date is None or payload.maturity_date is None:
                raise ValueError("Term deposit updates require principal, annual rate, start date, and maturity date")
            asset.principal_amount = payload.principal_amount
            asset.interest_rate_annual = payload.interest_rate_annual / 100 if payload.interest_rate_annual > 1 else payload.interest_rate_annual
            asset.start_date = payload.start_date
            asset.maturity_date = payload.maturity_date
            asset.bank_name = payload.bank_name
            if asset.maturity_date < asset.start_date:
                raise ValueError("Maturity date must be on or after start date")

        self.db.commit()
        self.db.refresh(asset)
        return asset

    def archive_asset(self, asset_id: int) -> Asset:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise ValueError("Asset not found")
        asset.enabled = False
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def delete_asset_if_safe(self, asset_id: int) -> None:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise ValueError("Asset not found")
        has_dependencies = any(
            [
                len(asset.lots) > 0,
                len(asset.market_quotes) > 0,
                len(asset.outlook_snapshots) > 0,
                len(asset.alert_rules) > 0,
            ]
        )
        if has_dependencies or asset.asset_mode != AssetMode.WATCHLIST:
            raise ValueError("Hard delete is only allowed for dependency-free watchlist assets")
        self.db.delete(asset)
        self.db.commit()

    def _create_default_polling_rule(self, asset: Asset) -> None:
        if asset.asset_mode not in {AssetMode.OWNED, AssetMode.WATCHLIST}:
            return
        if asset.asset_type in {AssetType.CASH, AssetType.TERM_DEPOSIT}:
            return
        if asset.asset_type not in POLL_CAPABLE_TYPES:
            return
        if any(rule.asset_id == asset.id for rule in self.polling_repo.list_all()):
            return
        defaults = self.settings_repo.get_first()
        interval = defaults.default_poll_every_minutes if defaults else 5
        market_hours = defaults.use_market_hours_default if defaults else False
        # First-run semantics: both timestamps are NULL so newly created assets are considered ready
        # for immediate first polling by a future scheduler.
        self.polling_repo.add(
            PollingRule(
                asset_id=asset.id,
                poll_every_minutes=interval,
                market_hours_only=market_hours,
                enabled=True,
                last_polled_at_utc=None,
                next_due_at_utc=None,
            )
        )
