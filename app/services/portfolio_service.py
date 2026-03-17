from decimal import Decimal

from app.models.asset import Asset
from app.repositories.lot_repo import LotRepository
from app.schemas.dashboard import AssetValuation, OwnedAssetRow


class PortfolioService:
    def __init__(self, lot_repo: LotRepository):
        self.lot_repo = lot_repo

    def aggregate_asset(
        self,
        asset: Asset,
        portfolio_base_currency: str,
        latest_quote_price: Decimal | None = None,
        fx_rate_to_base: Decimal | None = None,
        source_status: str = "missing",
        freshness_status: str = "unknown",
    ) -> OwnedAssetRow:
        lots = self.lot_repo.list_for_asset(asset.id)
        total_quantity = sum((lot.quantity for lot in lots), Decimal("0"))
        total_fees = sum((lot.fees for lot in lots), Decimal("0"))
        total_buy_value_ex_fees = sum((lot.quantity * lot.buy_price for lot in lots), Decimal("0"))
        total_invested_value_including_fees = total_buy_value_ex_fees + total_fees
        weighted_avg_buy_price_ex_fees = (total_buy_value_ex_fees / total_quantity) if total_quantity > 0 else Decimal("0")
        cost_basis_per_unit_including_fees = (total_invested_value_including_fees / total_quantity) if total_quantity > 0 else Decimal("0")

        quote_currency = asset.quote_currency.upper()
        base_currency = portfolio_base_currency.upper()
        value_in_quote = (total_quantity * latest_quote_price) if latest_quote_price is not None else None
        fx_status = "not_required" if quote_currency == base_currency else "available"
        valuation_warning = None

        if quote_currency != base_currency and fx_rate_to_base is None:
            fx_status = "missing"
            valuation_warning = "FX conversion unavailable"

        can_convert_to_base = value_in_quote is not None and (quote_currency == base_currency or fx_rate_to_base is not None)
        if not can_convert_to_base:
            value_in_base = None
            unrealized_pl_base = None
        elif quote_currency == base_currency:
            value_in_base = value_in_quote
            unrealized_pl_base = value_in_base - total_invested_value_including_fees
        else:
            value_in_base = value_in_quote * fx_rate_to_base
            unrealized_pl_base = value_in_base - total_invested_value_including_fees

        valuation = AssetValuation(
            quote_currency=quote_currency,
            base_currency=base_currency,
            quote_price=latest_quote_price,
            fx_rate_to_base=fx_rate_to_base,
            value_in_quote=value_in_quote,
            value_in_base=value_in_base,
            unrealized_pl_base=unrealized_pl_base,
            has_quote=latest_quote_price is not None,
            has_base_value=value_in_base is not None,
            fx_status=fx_status,
            source_status=source_status,
            freshness_status=freshness_status,
            valuation_warning=valuation_warning,
        )

        return OwnedAssetRow(
            asset_id=asset.id,
            asset_name=asset.display_name,
            asset_type=asset.asset_type.value,
            total_quantity=total_quantity,
            weighted_avg_buy_price_ex_fees=weighted_avg_buy_price_ex_fees,
            total_fees=total_fees,
            total_invested_value_including_fees=total_invested_value_including_fees,
            cost_basis_per_unit_including_fees=cost_basis_per_unit_including_fees,
            lot_count=len(lots),
            valuation=valuation,
        )
