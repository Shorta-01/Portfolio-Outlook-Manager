from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.action_snapshot import ActionSnapshot
from app.models.alert_rule import AlertRule
from app.models.market_quote import MarketQuote
from app.models.outlook_snapshot import OutlookSnapshot
from app.schemas.asset import AssetCreate
from app.services.alert_engine_service import AlertEngineService
from app.services.instrument_service import InstrumentService
from app.models.asset import AssetMode, AssetType
from app.repositories.alert_event_repo import AlertEventRepository
from app.services.status_service import StatusService


def _asset(db_session, name="A", mode=AssetMode.OWNED, typ=AssetType.STOCK, ccy="EUR"):
    return InstrumentService(db_session).create_asset(AssetCreate(display_name=name, asset_type=typ, asset_mode=mode, quote_currency=ccy))


def _rule(db_session, rule_type: str, asset_id: int | None, threshold: str | None = None, cooldown: int = 60):
    db_session.add(AlertRule(rule_type=rule_type, asset_id=asset_id, severity="medium", threshold_value=threshold, cooldown_minutes=cooldown, enabled=True))
    db_session.commit()


def _quote(db_session, asset_id: int, price: str, minutes_ago: int = 0):
    db_session.add(MarketQuote(asset_id=asset_id, provider_name="seed", price=Decimal(price), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow() - timedelta(minutes=minutes_ago), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.commit()


def test_price_rules_and_dedupe_and_cooldown(db_session):
    asset = _asset(db_session)
    _rule(db_session, "price_up_pct", asset.id, "5")
    _quote(db_session, asset.id, "100", 2)
    _quote(db_session, asset.id, "106", 1)
    svc = AlertEngineService(db_session)
    first = svc.run_once()
    db_session.commit()
    second = svc.run_once()
    assert first["created"] == 1
    assert second["created"] == 0


def test_price_down_and_crossing_and_resolve(db_session):
    asset = _asset(db_session, "B")
    _rule(db_session, "price_down_pct", asset.id, "5")
    _rule(db_session, "price_above", asset.id, "100")
    _rule(db_session, "price_below", asset.id, "90")
    _quote(db_session, asset.id, "95", 3)
    _quote(db_session, asset.id, "105", 2)
    assert AlertEngineService(db_session).run_once()["created"] >= 1
    _quote(db_session, asset.id, "89", 1)
    result = AlertEngineService(db_session).run_once()
    db_session.commit()
    assert result["created"] >= 1


def test_outlook_action_stale_incomplete_maturity(db_session):
    a1 = _asset(db_session, "C")
    a2 = _asset(db_session, "D", ccy="USD")
    td = InstrumentService(db_session).create_asset(AssetCreate(
        display_name="TD",
        asset_type=AssetType.TERM_DEPOSIT,
        asset_mode=AssetMode.TERM_DEPOSIT,
        quote_currency="EUR",
        principal_amount=Decimal("1000"),
        interest_rate_annual=Decimal("0.05"),
        start_date=date.today() - timedelta(days=20),
        maturity_date=date.today() + timedelta(days=10),
    ))

    for rt, aid, th in [
        ("outlook_changed", a1.id, None),
        ("action_changed", a1.id, None),
        ("quote_stale", a1.id, None),
        ("incomplete_valuation", a2.id, None),
        ("maturity_soon", td.id, None),
    ]:
        _rule(db_session, rt, aid, th)

    db_session.add_all([
        OutlookSnapshot(asset_id=a1.id, short_term_outlook="bullish", medium_term_outlook="neutral", confidence="medium", urgency="low", reason_summary="a", risk_note="r", short_term_score=0.4, medium_term_score=0.3, model_version="v1"),
        OutlookSnapshot(asset_id=a1.id, short_term_outlook="bearish", medium_term_outlook="neutral", confidence="medium", urgency="low", reason_summary="a", risk_note="r", short_term_score=0.2, medium_term_score=0.1, model_version="v1"),
        ActionSnapshot(asset_id=a1.id, action_label="buy", action_score=0.4, invalidation_note="x", key_level_up=None, key_level_down=None, model_version="v1"),
        ActionSnapshot(asset_id=a1.id, action_label="hold", action_score=0.1, invalidation_note="x", key_level_up=None, key_level_down=None, model_version="v1"),
        MarketQuote(asset_id=a1.id, provider_name="seed", price=Decimal("100"), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow() - timedelta(days=2), freshness_status="unknown", interval_type="spot", is_backfill=False),
        MarketQuote(asset_id=a2.id, provider_name="seed", price=Decimal("100"), quote_currency="USD", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False),
    ])
    db_session.commit()

    result = AlertEngineService(db_session).run_once()
    db_session.commit()
    assert result["created"] >= 5


def test_read_resolve_filters_unread_and_status_metrics(db_session):
    asset = _asset(db_session, "E")
    _rule(db_session, "price_up_pct", asset.id, "1")
    _quote(db_session, asset.id, "100", 2)
    _quote(db_session, asset.id, "102", 1)
    AlertEngineService(db_session).run_once()
    db_session.commit()

    repo = AlertEventRepository(db_session)
    alerts = repo.list_filtered(unread_only=True)
    assert len(alerts) == 1
    repo.mark_read(alerts[0].id)
    repo.resolve(alerts[0].id)
    db_session.commit()

    assert repo.unread_count() == 0
    assert repo.active_count() == 0
    status = StatusService(db_session).build()
    assert status["unread_alert_count"] == 0
    assert "total_alert_rules" in status
