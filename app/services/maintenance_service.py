from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetMode, AssetType
from app.repositories.asset_repo import AssetRepository
from app.repositories.lot_repo import LotRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.services.dashboard_service import DashboardService


@dataclass
class MaintenanceIssue:
    label: str
    asset_id: int
    asset_name: str
    detail: str
    next_action: str
    severity: str = "warning"


class MaintenanceService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.lot_repo = LotRepository(db)
        self.quote_repo = MarketQuoteRepository(db)
        self.dashboard_service = DashboardService(db)

    def scan(self) -> dict:
        issues: list[MaintenanceIssue] = []
        assets = self.asset_repo.list_all()
        assets_by_id = {a.id: a for a in assets}

        for asset in assets:
            if not asset.enabled:
                continue
            if asset.asset_mode == AssetMode.OWNED:
                lots = self.lot_repo.list_for_asset(asset.id)
                if len(lots) == 0:
                    issues.append(MaintenanceIssue(
                        label="Owned asset has no lots",
                        asset_id=asset.id,
                        asset_name=asset.display_name,
                        detail="The asset is in owned mode but has no lots, so holdings math will be zero.",
                        next_action="Add at least one lot or archive the asset.",
                    ))

            if asset.asset_mode in {AssetMode.OWNED, AssetMode.WATCHLIST} and asset.asset_type not in {AssetType.CASH, AssetType.TERM_DEPOSIT}:
                if (asset.provider_symbol_primary or "").strip() == "" and (asset.isin or "").strip() == "":
                    issues.append(MaintenanceIssue(
                        label="Lookup unresolved",
                        asset_id=asset.id,
                        asset_name=asset.display_name,
                        detail="No provider symbol or ISIN is available for lookup/backfill.",
                        next_action="Edit the asset and set ISIN or provider symbol.",
                    ))

            if asset.asset_mode == AssetMode.WATCHLIST:
                latest = self.quote_repo.latest_for_asset(asset.id)
                if latest is None or latest.provider_timestamp_utc < datetime.utcnow() - timedelta(days=14):
                    issues.append(MaintenanceIssue(
                        label="Stale watchlist quote",
                        asset_id=asset.id,
                        asset_name=asset.display_name,
                        detail="Watchlist quote data is missing or stale (>14 days).",
                        next_action="Backfill or review provider symbol mapping.",
                    ))

            if asset.asset_mode == AssetMode.OWNED:
                valuation = self.dashboard_service.valuation_service.aggregate_owned_asset(asset, self.dashboard_service._base_currency())
                if valuation.valuation_warning is not None:
                    age_days = (datetime.utcnow() - asset.created_at_utc).days
                    if age_days >= 7:
                        issues.append(MaintenanceIssue(
                            label="Incomplete valuation",
                            asset_id=asset.id,
                            asset_name=asset.display_name,
                            detail=f"Valuation remains incomplete ({valuation.valuation_warning}).",
                            next_action="Backfill quotes / FX and verify mapping.",
                        ))

        issues.extend(self._duplicate_like_issues([a for a in assets if a.enabled]))

        return {
            "issues": issues,
            "issue_count": len(issues),
            "scanned_at_utc": datetime.utcnow(),
            "archived_asset_count": sum(1 for a in assets if not a.enabled),
        }

    def _duplicate_like_issues(self, assets: list[Asset]) -> list[MaintenanceIssue]:
        issues: list[MaintenanceIssue] = []
        by_isin: dict[str, list[Asset]] = defaultdict(list)
        by_signature: dict[tuple[str, str, str, str], list[Asset]] = defaultdict(list)

        for asset in assets:
            if asset.isin:
                by_isin[asset.isin.strip().upper()].append(asset)
            sig = (
                asset.display_name.strip().lower(),
                asset.asset_type.value,
                asset.quote_currency.strip().upper(),
                (asset.exchange or "").strip().upper(),
            )
            by_signature[sig].append(asset)

        for isin, group in by_isin.items():
            if len(group) > 1:
                ids = ", ".join(str(a.id) for a in group)
                for asset in group:
                    issues.append(MaintenanceIssue(
                        label="Duplicate-like ISIN",
                        asset_id=asset.id,
                        asset_name=asset.display_name,
                        detail=f"ISIN {isin} appears on multiple assets ({ids}).",
                        next_action="Review duplicates and archive/deactivate extras.",
                    ))

        for sig, group in by_signature.items():
            if len(group) > 1:
                ids = ", ".join(str(a.id) for a in group)
                for asset in group:
                    issues.append(MaintenanceIssue(
                        label="Duplicate-like identity",
                        asset_id=asset.id,
                        asset_name=asset.display_name,
                        detail=f"Name/type/currency/exchange signature repeats across assets ({ids}).",
                        next_action="Review possible duplicates before adding new lots.",
                        severity="info",
                    ))
        return issues
