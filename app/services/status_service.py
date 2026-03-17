from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.asset_repo import AssetRepository
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.repositories.settings_repo import SettingsRepository


class StatusService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.polling_repo = PollingRuleRepository(db)
        self.settings_repo = SettingsRepository(db)

    def database_reachable(self) -> bool:
        try:
            self.db.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            return False

    def build(self) -> dict:
        return {
            "app_status": "ok",
            "database_reachable": self.database_reachable(),
            "settings_present": self.settings_repo.get_first() is not None,
            "asset_counts": self.asset_repo.count_by_mode(),
            "polling_rule_count": self.polling_repo.count(),
            "scheduler_status": "placeholder",
            "provider_freshness": "placeholder",
        }
