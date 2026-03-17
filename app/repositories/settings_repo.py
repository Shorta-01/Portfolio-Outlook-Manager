from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_first(self) -> AppSetting | None:
        return self.db.execute(select(AppSetting)).scalar_one_or_none()

    def upsert(self, payload: dict) -> AppSetting:
        settings = self.get_first()
        if settings is None:
            settings = AppSetting(**payload)
            self.db.add(settings)
        else:
            for key, value in payload.items():
                setattr(settings, key, value)
        self.db.flush()
        return settings
