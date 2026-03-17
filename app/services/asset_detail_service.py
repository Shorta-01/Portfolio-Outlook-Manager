from sqlalchemy.orm import Session

from app.models.asset import AssetMode, AssetType
from app.repositories.asset_repo import AssetRepository
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.valuation_service import ValuationService


class AssetDetailService:
    def __init__(self, db: Session):
        self.asset_repo = AssetRepository(db)
        self.lot_repo = LotRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.valuation_service = ValuationService(self.lot_repo, MarketQuoteRepository(db), FXRateRepository(db))

    def build(self, asset_id: int) -> dict:
        asset = self.asset_repo.get(asset_id)
        if asset is None:
            raise ValueError("Asset not found")

        is_owned = asset.asset_mode == AssetMode.OWNED
        lots = self.lot_repo.list_for_asset(asset.id) if is_owned else []
        base_currency = (self.settings_repo.get_first().portfolio_base_currency if self.settings_repo.get_first() else "EUR")

        aggregate = self.valuation_service.aggregate_owned_asset(asset, base_currency) if is_owned else None
        valuation = None
        maturity_value = None
        if asset.asset_mode in {AssetMode.CASH, AssetMode.TERM_DEPOSIT} or asset.asset_type in {AssetType.CASH, AssetType.TERM_DEPOSIT}:
            valuation = self.valuation_service.value_for_asset(
                asset,
                aggregate.total_quantity if aggregate else 0,
                aggregate.total_invested_value_including_fees if aggregate else (asset.principal_amount or 0),
                base_currency,
            )
        if asset.asset_type == AssetType.TERM_DEPOSIT or asset.asset_mode == AssetMode.TERM_DEPOSIT:
            maturity_value = self.valuation_service.maturity_value(asset)

        return {
            "asset": asset,
            "lots": lots,
            "aggregate": aggregate,
            "valuation": valuation,
            "maturity_value": maturity_value,
            "is_owned": is_owned,
            "is_watchlist": asset.asset_mode == AssetMode.WATCHLIST,
            "is_cash": asset.asset_mode == AssetMode.CASH or asset.asset_type == AssetType.CASH,
            "is_term_deposit": asset.asset_mode == AssetMode.TERM_DEPOSIT or asset.asset_type == AssetType.TERM_DEPOSIT,
        }
