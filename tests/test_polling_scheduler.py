from datetime import datetime, timedelta
from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.providers.types import NormalizedQuote
from app.repositories.polling_rule_repo import PollingRuleRepository
from app.scheduler.due_logic import compute_next_due, is_due
from app.scheduler.jobs import run_polling_cycle
from app.schemas.asset import AssetCreate
from app.services.instrument_service import InstrumentService


class FakeProvider:
    def __init__(self, *_args, **_kwargs):
        pass

    def fetch_latest_quote(self, asset):
        return NormalizedQuote("fake", "X", Decimal("12"), asset.quote_currency, datetime.utcnow(), "spot", {})

    def fetch_latest_fx(self, *_args, **_kwargs):
        return None


def test_due_logic_and_next_due_update(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="P", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR", is_manual_asset=False))
    rule = PollingRuleRepository(db_session).list_all()[0]
    now = datetime.utcnow()
    assert is_due(rule, now) is True
    nxt = compute_next_due(rule, now)
    assert nxt > now


def test_manual_poll_once_stores_latest_quote(db_session, monkeypatch):
    InstrumentService(db_session).create_asset(AssetCreate(display_name="P2", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR", is_manual_asset=False))
    monkeypatch.setattr("app.scheduler.jobs.FallbackProvider", lambda providers: FakeProvider())
    result = run_polling_cycle(db_session)
    assert result["ok"] is True
    assert result["processed"] == 1
    rule = PollingRuleRepository(db_session).list_all()[0]
    assert rule.next_due_at_utc is not None
