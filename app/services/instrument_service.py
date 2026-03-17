from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetMode, AssetType
from app.models.polling_rule import PollingRule
from app.repositories.asset_repo import AssetRepository
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.asset import AssetCreate
from app.services.asset_identity_service import AssetIdentityService

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

    def _create_default_polling_rule(self, asset: Asset) -> None:
        if asset.asset_mode not in {AssetMode.OWNED, AssetMode.WATCHLIST}:
            return
        if asset.asset_type in {AssetType.CASH, AssetType.TERM_DEPOSIT}:
            return
        if asset.asset_type not in POLL_CAPABLE_TYPES:
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
