from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.dashboard import SummaryCards
from app.services.valuation_service import ValuationService
from app.services.outlook_service import OutlookService


class DashboardService:
    def __init__(self, db: Session):
        self.asset_repo = AssetRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.valuation_service = ValuationService(LotRepository(db), MarketQuoteRepository(db), FXRateRepository(db))
        self.outlook_service = OutlookService(db)

    def _base_currency(self) -> str:
        settings = self.settings_repo.get_first()
        return settings.portfolio_base_currency if settings else "EUR"

    def owned_rows(self):
        assets = self.asset_repo.list_by_mode(AssetMode.OWNED)
        base_currency = self._base_currency()
        rows = []
        for asset in assets:
            row = self.valuation_service.aggregate_owned_asset(asset, base_currency)
            outlook, action = self.outlook_service.latest_for_asset(asset.id)
            row.outlook = outlook.short_term_outlook if outlook else None
            row.suggested_action = action.action_label if action else None
            row.confidence = outlook.confidence if outlook else None
            latest_quote = self.valuation_service.quote_repo.latest_for_asset(asset.id)
            row.last_update_utc = latest_quote.provider_timestamp_utc if latest_quote else None
            row.quote_currency = asset.quote_currency
            row.isin = asset.isin
            row.provider_symbol = asset.provider_symbol_primary
            row.urgency = outlook.urgency if outlook else None
            rows.append(row)
        return rows

    def watchlist_rows(self):
        rows = []
        for asset in self.asset_repo.list_by_mode(AssetMode.WATCHLIST):
            outlook, action = self.outlook_service.latest_for_asset(asset.id)
            latest_quote = self.valuation_service.quote_repo.latest_for_asset(asset.id)
            rows.append({
                "id": asset.id,
                "display_name": asset.display_name,
                "asset_type": asset.asset_type.value,
                "quote_currency": asset.quote_currency,
                "isin": asset.isin,
                "provider_symbol": asset.provider_symbol_primary,
                "outlook": outlook.short_term_outlook if outlook else None,
                "suggested_action": action.action_label if action else None,
                "confidence": outlook.confidence if outlook else None,
                "urgency": outlook.urgency if outlook else None,
                "source_label": latest_quote.provider_name if latest_quote else "Unknown",
                "freshness_status": self.valuation_service._freshness_from_timestamp(latest_quote.provider_timestamp_utc) if latest_quote else "unknown",
                "last_update_utc": latest_quote.provider_timestamp_utc if latest_quote else None,
            })
        return rows

    def query_owned_rows(self, params: dict[str, str]) -> list[Any]:
        rows = self.owned_rows()
        q = (params.get("q") or "").strip().lower()
        if q:
            rows = [
                row
                for row in rows
                if q in row.asset_name.lower() or q in (row.isin or "").lower() or q in (row.provider_symbol or "").lower()
            ]

        if params.get("asset_type"):
            rows = [r for r in rows if r.asset_type == params["asset_type"]]
        if params.get("currency"):
            rows = [r for r in rows if (r.quote_currency or "").upper() == params["currency"].upper()]
        if params.get("outlook"):
            rows = [r for r in rows if (r.outlook or "") == params["outlook"]]
        if params.get("action"):
            rows = [r for r in rows if (r.suggested_action or "") == params["action"]]
        if params.get("freshness"):
            rows = [r for r in rows if (r.freshness_status or "") == params["freshness"]]
        if params.get("source"):
            rows = [r for r in rows if (r.source_label or "") == params["source"]]
        if params.get("incomplete_only") == "1":
            rows = [r for r in rows if not r.has_base_value]

        key = params.get("sort", "asset_name")
        desc = params.get("dir", "asc") == "desc"

        def sort_key(row: Any):
            mapping = {
                "asset_name": row.asset_name,
                "asset_type": row.asset_type,
                "value_now": row.value_now or Decimal("-999999999"),
                "pl_amount": row.unrealized_pl_amount or Decimal("-999999999"),
                "pl_percent": row.unrealized_pl_percent or Decimal("-999999999"),
                "confidence": row.confidence or "",
                "urgency": row.urgency or "",
                "last_update": row.last_update_utc or "",
            }
            return mapping.get(key, row.asset_name)

        rows.sort(key=sort_key, reverse=desc)
        return rows

    def query_watchlist_rows(self, params: dict[str, str]) -> list[dict[str, Any]]:
        rows = self.watchlist_rows()
        q = (params.get("q") or "").strip().lower()
        if q:
            rows = [
                row
                for row in rows
                if q in row["display_name"].lower() or q in (row.get("isin") or "").lower() or q in (row.get("provider_symbol") or "").lower()
            ]
        for key, field in [("asset_type", "asset_type"), ("currency", "quote_currency"), ("outlook", "outlook"), ("action", "suggested_action"), ("freshness", "freshness_status"), ("source", "source_label")]:
            if params.get(key):
                rows = [r for r in rows if (r.get(field) or "") == params[key]]
        sort = params.get("sort", "display_name")
        desc = params.get("dir", "asc") == "desc"
        rows.sort(key=lambda r: r.get(sort) or "", reverse=desc)
        return rows

    def summary_cards(self) -> SummaryCards:
        rows = self.owned_rows()
        total_invested = sum((row.total_invested_value_including_fees for row in rows), Decimal("0"))
        rows_with_base = [row for row in rows if row.has_base_value and row.value_now is not None]
        total_current = sum((row.value_now for row in rows_with_base), Decimal("0")) if rows_with_base else None
        omitted_from_totals_count = sum(1 for row in rows if not row.has_base_value)
        totals_complete = omitted_from_totals_count == 0

        if not rows:
            total_current = Decimal("0")
            pl_amount = Decimal("0")
        else:
            pl_amount = (total_current - total_invested) if totals_complete and total_current is not None else None
        pl_percent = (pl_amount / total_invested * Decimal("100")) if pl_amount is not None and total_invested > 0 else None
        missing_fx_asset_count = sum(1 for row in rows if row.fx_status == "missing")
        missing_quote_asset_count = sum(1 for row in rows if not row.has_quote)
        return SummaryCards(
            total_invested=total_invested,
            total_current_value=total_current,
            total_unrealized_pl_amount=pl_amount,
            total_unrealized_pl_percent=pl_percent,
            totals_complete=totals_complete,
            missing_fx_asset_count=missing_fx_asset_count,
            missing_quote_asset_count=missing_quote_asset_count,
            omitted_from_totals_count=omitted_from_totals_count,
        )
