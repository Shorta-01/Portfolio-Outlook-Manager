from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Portfolio Outlook Manager"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
