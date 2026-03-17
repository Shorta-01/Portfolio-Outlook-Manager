import csv
import logging
import shutil
from datetime import datetime
from io import StringIO
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.asset import AssetMode
from app.repositories.asset_repo import AssetRepository
from app.repositories.lot_repo import LotRepository
from app.services.dashboard_service import DashboardService
from app.services.scheduler_state import scheduler_state

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, db: Session):
        self.asset_repo = AssetRepository(db)
        self.lot_repo = LotRepository(db)
        self.dashboard_service = DashboardService(db)

    def portfolio_csv(self) -> str:
        rows = self.dashboard_service.owned_rows()
        out = StringIO()
        w = csv.writer(out)
        w.writerow([
            "asset_id", "asset_name", "asset_type", "quote_currency", "isin", "provider_symbol",
            "quantity", "cost_basis_total", "value_now_base", "unrealized_pl_amount", "unrealized_pl_percent",
            "outlook", "suggested_action", "confidence", "urgency", "freshness", "source",
        ])
        for r in rows:
            w.writerow([
                r.asset_id, r.asset_name, r.asset_type, r.quote_currency or "", r.isin or "", r.provider_symbol or "",
                r.total_quantity, r.total_invested_value_including_fees, r.value_now if r.has_base_value else "",
                r.unrealized_pl_amount if r.has_base_value else "", r.unrealized_pl_percent if r.has_base_value else "",
                r.outlook or "", r.suggested_action or "", r.confidence or "", r.urgency or "", r.freshness_status, r.source_label,
            ])
        return out.getvalue()

    def watchlist_csv(self) -> str:
        rows = self.dashboard_service.watchlist_rows()
        out = StringIO()
        w = csv.writer(out)
        w.writerow(["asset_id", "display_name", "asset_type", "quote_currency", "isin", "provider_symbol", "outlook", "suggested_action", "confidence", "urgency", "freshness", "source"])
        for r in rows:
            w.writerow([r["id"], r["display_name"], r["asset_type"], r.get("quote_currency") or "", r.get("isin") or "", r.get("provider_symbol") or "", r.get("outlook") or "", r.get("suggested_action") or "", r.get("confidence") or "", r.get("urgency") or "", r.get("freshness_status") or "", r.get("source_label") or ""])
        return out.getvalue()

    def lots_csv(self) -> str:
        out = StringIO()
        w = csv.writer(out)
        w.writerow(["asset_id", "asset_name", "quantity", "buy_price", "buy_currency", "buy_date", "fees", "notes"])
        for a in self.asset_repo.list_by_mode(AssetMode.OWNED):
            for lot in self.lot_repo.list_for_asset(a.id):
                w.writerow([a.id, a.display_name, lot.quantity, lot.buy_price, lot.buy_currency, lot.buy_date, lot.fees, lot.notes or ""])
        return out.getvalue()

    def create_sqlite_backup(self) -> Path:
        db_path = Path(settings.database_url.replace("sqlite:///", ""))
        backup_dir = Path(settings.backup_dir)
        backup_dir.mkdir(exist_ok=True)
        target = backup_dir / f"portfolio_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sqlite3"
        shutil.copy2(db_path, target)
        scheduler_state.mark_job_success("backup")
        scheduler_state.last_backup_path = str(target)
        logger.info("Database backup created path=%s", target)
        return target

    def latest_backup_metadata(self) -> dict:
        backup_dir = Path(settings.backup_dir)
        if not backup_dir.exists():
            return {"timestamp_utc": None, "path": None}
        backups = sorted(backup_dir.glob("portfolio_backup_*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            return {"timestamp_utc": None, "path": None}
        latest = backups[0]
        return {"timestamp_utc": datetime.utcfromtimestamp(latest.stat().st_mtime), "path": str(latest)}
