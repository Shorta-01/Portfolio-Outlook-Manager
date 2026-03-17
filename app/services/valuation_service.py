from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.asset import Asset, AssetMode, AssetType
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.schemas.dashboard import OwnedAssetRow
from app.services.fx_service import FXService

FRESH_SECS = 15 * 60
DELAYED_SECS = 24 * 60 * 60

MARKET_PRICED_TYPES = {
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


@dataclass
class ValuationResult:
    current_price_quote_currency: Decimal | None
    value_now_quote_currency: Decimal
    value_now_base_currency: Decimal
    unrealized_pl_amount: Decimal
    unrealized_pl_percent: Decimal | None
    source_label: str
    freshness_status: str


class ValuationService:
    def __init__(self, lot_repo: LotRepository, quote_repo: MarketQuoteRepository, fx_repo: FXRateRepository):
        self.lot_repo = lot_repo
        self.quote_repo = quote_repo
        self.fx_service = FXService(fx_repo)

    def aggregate_owned_asset(self, asset: Asset, base_currency: str) -> OwnedAssetRow:
        lots = self.lot_repo.list_for_asset(asset.id)
        total_quantity = sum((lot.quantity for lot in lots), Decimal("0"))
        total_fees = sum((lot.fees for lot in lots), Decimal("0"))
        total_buy_value_ex_fees = sum((lot.quantity * lot.buy_price for lot in lots), Decimal("0"))
        total_invested = total_buy_value_ex_fees + total_fees
        avg_buy = (total_buy_value_ex_fees / total_quantity) if total_quantity > 0 else Decimal("0")
        cost_basis = (total_invested / total_quantity) if total_quantity > 0 else Decimal("0")

        valuation = self.value_for_asset(asset, total_quantity, total_invested, base_currency)
        return OwnedAssetRow(
            asset_id=asset.id,
            asset_name=asset.display_name,
            asset_type=asset.asset_type.value,
            total_quantity=total_quantity,
            weighted_avg_buy_price_ex_fees=avg_buy,
            total_fees=total_fees,
            total_invested_value_including_fees=total_invested,
            cost_basis_per_unit_including_fees=cost_basis,
            lot_count=len(lots),
            current_price=valuation.current_price_quote_currency,
            value_now=valuation.value_now_base_currency,
            value_now_quote_currency=valuation.value_now_quote_currency,
            unrealized_pl_amount=valuation.unrealized_pl_amount,
            unrealized_pl_percent=valuation.unrealized_pl_percent,
            freshness_status=valuation.freshness_status,
            source_label=valuation.source_label,
        )

    def value_for_asset(self, asset: Asset, total_quantity: Decimal, invested_value: Decimal, base_currency: str) -> ValuationResult:
        if asset.asset_mode == AssetMode.CASH or asset.asset_type == AssetType.CASH:
            amount = asset.current_amount or Decimal("0")
            pl_amount = Decimal("0")
            return ValuationResult(amount, amount, amount, pl_amount, Decimal("0"), "Manual", "manual")

        if asset.asset_mode == AssetMode.TERM_DEPOSIT or asset.asset_type == AssetType.TERM_DEPOSIT:
            principal = asset.principal_amount or Decimal("0")
            accrued = self._accrued_term_deposit_value(asset)
            pl = accrued - principal
            pl_pct = (pl / principal * Decimal("100")) if principal > 0 else None
            return ValuationResult(None, accrued, accrued, pl, pl_pct, "Contract", "contract")

        if asset.asset_type in MARKET_PRICED_TYPES:
            quote = self.quote_repo.latest_for_asset(asset.id)
            if quote is None:
                return ValuationResult(None, Decimal("0"), Decimal("0"), -invested_value, None, "Unknown", "unknown")
            value_quote = total_quantity * quote.price
            converted = self.fx_service.convert(value_quote, quote.quote_currency, base_currency)
            value_base = converted if converted is not None else Decimal("0")
            pl = value_base - invested_value
            pl_pct = (pl / invested_value * Decimal("100")) if invested_value > 0 else None
            return ValuationResult(
                quote.price,
                value_quote,
                value_base,
                pl,
                pl_pct,
                quote.provider_name,
                self._freshness_from_timestamp(quote.provider_timestamp_utc),
            )

        return ValuationResult(None, Decimal("0"), Decimal("0"), Decimal("0"), None, "Unknown", "unknown")

    def _freshness_from_timestamp(self, provider_timestamp_utc: datetime) -> str:
        now = datetime.now(timezone.utc)
        ts = provider_timestamp_utc.replace(tzinfo=timezone.utc) if provider_timestamp_utc.tzinfo is None else provider_timestamp_utc
        age_seconds = (now - ts).total_seconds()
        if age_seconds <= FRESH_SECS:
            return "fresh"
        if age_seconds <= DELAYED_SECS:
            return "delayed"
        return "stale"

    def _accrued_term_deposit_value(self, asset: Asset) -> Decimal:
        principal = asset.principal_amount or Decimal("0")
        annual_rate = asset.interest_rate_annual or Decimal("0")
        if not asset.start_date or not asset.maturity_date:
            return principal
        today = date.today()
        end = min(today, asset.maturity_date)
        total_days = max((asset.maturity_date - asset.start_date).days, 1)
        elapsed = max((end - asset.start_date).days, 0)
        total_interest = principal * annual_rate * Decimal(total_days) / Decimal("365")
        accrued_interest = total_interest * Decimal(elapsed) / Decimal(total_days)
        return principal + accrued_interest

    def maturity_value(self, asset: Asset) -> Decimal:
        principal = asset.principal_amount or Decimal("0")
        annual_rate = asset.interest_rate_annual or Decimal("0")
        if not asset.start_date or not asset.maturity_date:
            return principal
        days = max((asset.maturity_date - asset.start_date).days, 0)
        return principal + (principal * annual_rate * Decimal(days) / Decimal("365"))
