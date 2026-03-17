from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Portfolio Outlook Manager"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    twelve_data_api_key: str = os.getenv("TWELVE_DATA_API_KEY", "")
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    backup_dir: str = os.getenv("BACKUP_DIR", "backups")
    retention_raw_quotes_days: int = int(os.getenv("RETENTION_RAW_QUOTES_DAYS", "30"))
    retention_normalized_quotes_days: int = int(os.getenv("RETENTION_NORMALIZED_QUOTES_DAYS", "365"))
    retention_fx_days: int = int(os.getenv("RETENTION_FX_DAYS", "365"))
    retention_outlook_snapshots_days: int = int(os.getenv("RETENTION_OUTLOOK_SNAPSHOTS_DAYS", "365"))
    retention_action_snapshots_days: int = int(os.getenv("RETENTION_ACTION_SNAPSHOTS_DAYS", "365"))
    retention_outlook_evaluations_days: int = int(os.getenv("RETENTION_OUTLOOK_EVALUATIONS_DAYS", "730"))
    retention_alert_events_days: int = int(os.getenv("RETENTION_ALERT_EVENTS_DAYS", "180"))
    app_version: str = os.getenv("APP_VERSION", "0.8.0-rc1")
    app_build: str = os.getenv("APP_BUILD", os.getenv("GIT_COMMIT", "local"))
    app_environment: str = os.getenv("APP_ENV", "beta")


settings = Settings()
