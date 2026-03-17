import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.asset import AssetType
from app.providers.fallback_provider import FallbackProvider
from app.providers.manual_provider import ManualProvider
from app.providers.twelve_data_provider import TwelveDataProvider
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.repositories.settings_repo import SettingsRepository
from app.scheduler.due_logic import compute_next_due, is_due
from app.scheduler.locks import poll_lock
from app.services.market_data_ingestion_service import MarketDataIngestionService
from app.services.scheduler_state import scheduler_state
from app.services.outlook_service import OutlookService

logger = logging.getLogger(__name__)


def run_polling_cycle(db: Session) -> dict:
    if not poll_lock.acquire():
        logger.info("Polling cycle skipped: previous run still active")
        return {"ok": False, "reason": "locked", "processed": 0}

    try:
        logger.info("Polling cycle started")
        now = datetime.utcnow()
        rules = PollingRuleRepository(db).list_due(now)
        ingestion = MarketDataIngestionService(db)
        provider = FallbackProvider([TwelveDataProvider(), ManualProvider(MarketQuoteRepository(db), FXRateRepository(db))])
        settings = SettingsRepository(db).get_first()
        base_currency = (settings.portfolio_base_currency if settings else "EUR").upper()
        processed = 0

        for rule in rules:
            asset = rule.asset
            if asset is None:
                continue
            if asset.asset_type in {AssetType.CASH, AssetType.TERM_DEPOSIT}:
                continue
            if not is_due(rule, now):
                continue

            quote = provider.fetch_latest_quote(asset)
            if quote is not None:
                ingestion.ingest_quote(asset.id, quote, is_backfill=False)
                processed += 1
                if quote.quote_currency.upper() != base_currency:
                    fx = provider.fetch_latest_fx(quote.quote_currency.upper(), base_currency)
                    if fx is not None:
                        ingestion.ingest_fx(fx)
            rule.last_polled_at_utc = now
            rule.next_due_at_utc = compute_next_due(rule, now)

        outlook_result = OutlookService(db).run_once_for_eligible_assets()
        db.commit()
        scheduler_state.last_successful_poll_utc = datetime.utcnow()
        logger.info("Polling cycle finished processed=%s", processed)
        return {"ok": True, "processed": processed, "outlook_processed": outlook_result["processed"]}
    except Exception:
        logger.exception("Polling cycle failed")
        db.rollback()
        return {"ok": False, "reason": "exception", "processed": 0}
    finally:
        poll_lock.release()


def run_polling_cycle_from_new_session() -> dict:
    with SessionLocal() as db:
        return run_polling_cycle(db)
