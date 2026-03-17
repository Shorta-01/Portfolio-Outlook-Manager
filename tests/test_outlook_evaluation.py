from datetime import datetime, timedelta
from decimal import Decimal

from app.models.market_quote import MarketQuote
from app.models.outlook_evaluation import OutlookEvaluation
from app.models.outlook_snapshot import OutlookSnapshot
from app.models.asset import AssetMode, AssetType
from app.repositories.outlook_evaluation_repo import OutlookEvaluationRepository
from app.repositories.outlook_snapshot_repo import OutlookSnapshotRepository
from app.schemas.asset import AssetCreate
from app.services.asset_detail_service import AssetDetailService
from app.services.instrument_service import InstrumentService
from app.services.outlook_evaluation_service import OutlookEvaluationService
from app.services.outlook_service import OutlookService
from app.services.status_service import StatusService
from app.routes.admin import run_outlook_evaluate_once


def _q(db_session, asset_id: int, when: datetime, price: str):
    db_session.add(
        MarketQuote(
            asset_id=asset_id,
            provider_name="seed",
            price=Decimal(price),
            quote_currency="EUR",
            provider_timestamp_utc=when,
            freshness_status="fresh",
            interval_type="spot",
            is_backfill=False,
        )
    )


def test_short_medium_and_neutral_evaluation(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Eval", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    now = datetime.utcnow()
    snap = OutlookSnapshot(
        asset_id=asset.id,
        timestamp_utc=now - timedelta(days=8),
        short_term_outlook="bullish",
        medium_term_outlook="bearish",
        confidence="high",
        urgency="medium",
        reason_summary="x",
        risk_note="x",
        short_term_score=0.4,
        medium_term_score=-0.4,
        model_version="v1",
    )
    db_session.add(snap)
    db_session.flush()
    _q(db_session, asset.id, snap.timestamp_utc, "100")
    _q(db_session, asset.id, snap.timestamp_utc + timedelta(hours=24), "101")
    _q(db_session, asset.id, snap.timestamp_utc + timedelta(days=7), "100.2")
    db_session.commit()

    result = OutlookEvaluationService(db_session).run_once()
    assert result["evaluated_outlook_count"] == 2

    repo = OutlookEvaluationRepository(db_session)
    short_eval = repo.get_by_snapshot_and_horizon(snap.id, "short")
    medium_eval = repo.get_by_snapshot_and_horizon(snap.id, "medium")
    assert short_eval is not None and short_eval.was_correct is True
    assert medium_eval is not None and medium_eval.was_correct is None


def test_duplicate_evaluation_prevention(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Dup", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    now = datetime.utcnow()
    snap = OutlookSnapshot(
        asset_id=asset.id,
        timestamp_utc=now - timedelta(days=8),
        short_term_outlook="bullish",
        medium_term_outlook="bullish",
        confidence="medium",
        urgency="low",
        reason_summary="r",
        risk_note="r",
        short_term_score=0.3,
        medium_term_score=0.3,
        model_version="v1",
    )
    db_session.add(snap)
    db_session.flush()
    _q(db_session, asset.id, snap.timestamp_utc, "100")
    _q(db_session, asset.id, snap.timestamp_utc + timedelta(days=8), "110")
    db_session.commit()

    service = OutlookEvaluationService(db_session)
    service.run_once()
    service.run_once()
    all_rows = db_session.query(OutlookEvaluation).all()
    assert len(all_rows) == 2


def test_snapshot_material_change_suppression(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="NoFlood", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    base = datetime.utcnow() - timedelta(hours=30)
    for i in range(30):
        _q(db_session, asset.id, base + timedelta(hours=i), str(100 + i))
    db_session.commit()

    svc = OutlookService(db_session)
    svc.run_once_for_eligible_assets()
    first = OutlookSnapshotRepository(db_session).count_rows()
    svc.run_once_for_eligible_assets()
    second = OutlookSnapshotRepository(db_session).count_rows()
    assert first == 1
    assert second == 1


def test_confidence_stats_asset_scorecard_and_status(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Stats", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    now = datetime.utcnow()
    s1 = OutlookSnapshot(asset_id=asset.id, timestamp_utc=now - timedelta(days=8), short_term_outlook="bullish", medium_term_outlook="bullish", confidence="high", urgency="low", reason_summary="r1", risk_note="r1", short_term_score=0.4, medium_term_score=0.5, model_version="v1")
    s2 = OutlookSnapshot(asset_id=asset.id, timestamp_utc=now - timedelta(days=9), short_term_outlook="bearish", medium_term_outlook="bearish", confidence="low", urgency="low", reason_summary="r2", risk_note="r2", short_term_score=-0.4, medium_term_score=-0.5, model_version="v1")
    db_session.add_all([s1, s2])
    db_session.flush()
    for s in (s1, s2):
        _q(db_session, asset.id, s.timestamp_utc, "100")
        _q(db_session, asset.id, s.timestamp_utc + timedelta(days=8), "90")
    db_session.commit()

    OutlookEvaluationService(db_session).run_once()
    detail = AssetDetailService(db_session).build(asset.id)
    assert detail["outlook_scorecard"]["accuracy"]["short"]["total"] >= 1
    assert isinstance(detail["outlook_scorecard"]["confidence"], list)

    status = StatusService(db_session).build()
    assert status["total_outlook_snapshots"] >= 2
    assert status["total_evaluated_outlooks"] >= 2


def test_admin_outlook_evaluation_run_once_path(db_session):
    response = run_outlook_evaluate_once(db_session)
    assert response.status_code == 303
