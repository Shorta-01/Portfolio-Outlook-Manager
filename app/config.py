from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Portfolio Outlook Manager"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    twelve_data_api_key: str = os.getenv("TWELVE_DATA_API_KEY", "")
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"


settings = Settings()
