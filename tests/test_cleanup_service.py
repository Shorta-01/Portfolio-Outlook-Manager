from datetime import datetime, timedelta

from app.models.action_snapshot import ActionSnapshot
from app.models.alert_event import AlertEvent
from app.models.asset import AssetMode, AssetType
from app.models.fx_rate import FXRate
from app.models.market_quote import MarketQuote
from app.models.market_quote_raw import MarketQuoteRaw
from app.models.outlook_evaluation import OutlookEvaluation
from app.models.outlook_snapshot import OutlookSnapshot
from app.schemas.asset import AssetCreate
from app.services.cleanup_service import CleanupService
from app.services.instrument_service import InstrumentService


def test_cleanup_prunes_old_rows_but_keeps_latest_per_asset(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="A", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    old = datetime.utcnow() - timedelta(days=900)
    new = datetime.utcnow() - timedelta(days=1)

    db_session.add(MarketQuoteRaw(asset_id=asset.id, provider_name="m", provider_symbol="A", payload_json={}, provider_timestamp_utc=old, ingested_at_utc=old, status="ok"))
    db_session.add(MarketQuote(asset_id=asset.id, provider_name="m", price=10, quote_currency="EUR", provider_timestamp_utc=old, ingested_at_utc=old, freshness_status="stale", interval_type="spot", is_backfill=True))
    db_session.add(MarketQuote(asset_id=asset.id, provider_name="m", price=11, quote_currency="EUR", provider_timestamp_utc=new, ingested_at_utc=new, freshness_status="fresh", interval_type="spot", is_backfill=False))
    db_session.add(FXRate(pair_code="USDEUR", base_currency="USD", quote_currency="EUR", rate=1.1, provider_name="m", provider_timestamp_utc=old, ingested_at_utc=old, interval_type="spot"))
    db_session.add(FXRate(pair_code="USDEUR", base_currency="USD", quote_currency="EUR", rate=1.2, provider_name="m", provider_timestamp_utc=new, ingested_at_utc=new, interval_type="spot"))
    snap = OutlookSnapshot(asset_id=asset.id, timestamp_utc=old, short_term_outlook="bullish", medium_term_outlook="bullish", confidence="medium", urgency="low", reason_summary="x", risk_note="x", short_term_score=0.1, medium_term_score=0.2, model_version="m", component_flags="{}", component_summary="{}", model_diagnostic_note="", volatility_state="normal")
    db_session.add(snap)
    db_session.flush()
    db_session.add(OutlookEvaluation(asset_id=asset.id, outlook_snapshot_id=snap.id, horizon_type="short", horizon_end_timestamp_utc=old, predicted_label="bullish", realized_return=0.2, realized_direction="bullish", was_correct=True, confidence_at_prediction="medium", confidence_bucket="medium", evaluation_note="ok", model_version="m", evaluation_timestamp_utc=old))
    db_session.add(ActionSnapshot(asset_id=asset.id, timestamp_utc=old, action_label="hold", action_score=0.3, invalidation_note="x", key_level_up=None, key_level_down=None, model_version="m"))
    db_session.add(ActionSnapshot(asset_id=asset.id, timestamp_utc=new, action_label="buy", action_score=0.7, invalidation_note="x", key_level_up=None, key_level_down=None, model_version="m"))
    db_session.commit()

    result = CleanupService(db_session).run_once()

    assert result.removed["market_quotes_raw"] >= 1
    assert db_session.query(MarketQuote).count() == 1
    assert db_session.query(FXRate).count() == 1
    assert db_session.query(ActionSnapshot).count() == 1


def test_cleanup_keeps_unread_or_active_alerts(db_session):
    old = datetime.utcnow() - timedelta(days=300)
    keep_unread = AlertEvent(timestamp_utc=old, severity="low", alert_type="t", title="u", message="u", dedupe_key="u", is_read=False, is_active=False)
    keep_active = AlertEvent(timestamp_utc=old, severity="low", alert_type="t", title="a", message="a", dedupe_key="a", is_read=True, is_active=True)
    prune = AlertEvent(timestamp_utc=old, severity="low", alert_type="t", title="p", message="p", dedupe_key="p", is_read=True, is_active=False, resolved_at_utc=old)
    db_session.add_all([keep_unread, keep_active, prune])
    db_session.commit()

    prune_id = prune.id
    keep_unread_id = keep_unread.id
    keep_active_id = keep_active.id
    result = CleanupService(db_session).run_once()

    assert result.removed["alert_events"] == 1
    ids = {row.id for row in db_session.query(AlertEvent).all()}
    assert keep_unread_id in ids
    assert keep_active_id in ids
    assert prune_id not in ids
