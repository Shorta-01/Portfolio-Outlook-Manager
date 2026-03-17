from datetime import datetime, timedelta
from decimal import Decimal

from app.forecasting.scoring import score_to_outlook
from app.forecasting.signals import build_signals
from app.forecasting.types import QuotePoint
from app.models.asset import AssetMode, AssetType
from app.models.market_quote import MarketQuote
from app.repositories.action_snapshot_repo import ActionSnapshotRepository
from app.repositories.outlook_snapshot_repo import OutlookSnapshotRepository
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.action_service import ActionService
from app.services.asset_detail_service import AssetDetailService
from app.services.dashboard_service import DashboardService
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService
from app.services.outlook_service import OutlookService
from app.services.status_service import StatusService


def _seed_quotes(db_session, asset_id: int, prices: list[str]):
    start = datetime.utcnow() - timedelta(hours=len(prices))
    for idx, px in enumerate(prices):
        db_session.add(
            MarketQuote(
                asset_id=asset_id,
                provider_name="seed",
                price=Decimal(px),
                quote_currency="EUR",
                provider_timestamp_utc=start + timedelta(hours=idx),
                freshness_status="fresh",
                interval_type="spot",
                is_backfill=False,
            )
        )
    db_session.commit()


def test_signal_trend_and_momentum_positive():
    now = datetime.utcnow()
    points = [QuotePoint(timestamp_utc=now - timedelta(hours=10 - i), price=100 + i) for i in range(10)]
    signals = build_signals(points, now)
    assert signals.trend > 0
    assert signals.momentum > 0


def test_volatility_penalty_behavior():
    now = datetime.utcnow()
    stable = [QuotePoint(timestamp_utc=now - timedelta(hours=20 - i), price=100.0 + (i * 0.01)) for i in range(20)]
    choppy = [QuotePoint(timestamp_utc=now - timedelta(hours=20 - i), price=(100.0 + (10 if i % 2 else -10))) for i in range(20)]
    assert build_signals(choppy, now).volatility_penalty > build_signals(stable, now).volatility_penalty


def test_insufficient_history_handling_lowers_confidence(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Thin", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    _seed_quotes(db_session, asset.id, ["100", "101"])
    OutlookService(db_session).run_once_for_eligible_assets()
    outlook = OutlookSnapshotRepository(db_session).get_latest_by_asset(asset.id)
    assert outlook is not None
    assert outlook.confidence == "low"


def test_score_to_label_mapping():
    assert score_to_outlook(0.4) == "bullish"
    assert score_to_outlook(-0.4) == "bearish"
    assert score_to_outlook(0.0) == "neutral"


def test_action_mapping():
    label, invalidation = ActionService().map_action(action_score=-0.8, key_level_up=110.0, key_level_down=90.0, medium_term_outlook="bearish")
    assert label == "Sell candidate"
    assert "110.0000" in invalidation


def test_outlook_snapshot_persistence_and_latest_retrieval(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Persist", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    _seed_quotes(db_session, asset.id, [str(100 + i) for i in range(25)])
    service = OutlookService(db_session)
    service.run_once_for_eligible_assets()
    latest = OutlookSnapshotRepository(db_session).get_latest_by_asset(asset.id)
    action = ActionSnapshotRepository(db_session).get_latest_by_asset(asset.id)
    assert latest is not None
    assert action is not None
    assert latest.short_term_outlook in {"bullish", "neutral", "bearish"}


def test_dashboard_and_watchlist_use_latest_outlook(db_session):
    owned = InstrumentService(db_session).create_asset(AssetCreate(display_name="Owned", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    watch = InstrumentService(db_session).create_asset(AssetCreate(display_name="Watch", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=owned.id, quantity="1", buy_price="100", buy_currency="EUR", buy_date="2024-01-01"))
    _seed_quotes(db_session, owned.id, [str(100 + i) for i in range(25)])
    _seed_quotes(db_session, watch.id, [str(200 + i) for i in range(25)])
    OutlookService(db_session).run_once_for_eligible_assets()

    dash = DashboardService(db_session)
    owned_row = dash.owned_rows()[0]
    watch_row = dash.watchlist_rows()[0]
    assert owned_row.outlook is not None
    assert watch_row["outlook"] is not None


def test_asset_detail_exposes_latest_outlook_fields(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Detail", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    _seed_quotes(db_session, asset.id, [str(50 + i) for i in range(25)])
    OutlookService(db_session).run_once_for_eligible_assets()
    model = AssetDetailService(db_session).build(asset.id)
    assert model["outlook"] is not None
    assert model["action"] is not None
    assert len(model["recent_outlook_history"]) >= 1


def test_cash_and_term_deposit_skipped(db_session):
    cash = InstrumentService(db_session).create_asset(AssetCreate(display_name="Cash", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR", current_amount="10"))
    td = InstrumentService(db_session).create_asset(AssetCreate(display_name="TD", asset_type=AssetType.TERM_DEPOSIT, asset_mode=AssetMode.TERM_DEPOSIT, quote_currency="EUR", principal_amount="100", interest_rate_annual="0.05", start_date="2024-01-01", maturity_date="2025-01-01"))
    result = OutlookService(db_session).run_once_for_eligible_assets()
    assert result["processed"] == 0
    assert OutlookSnapshotRepository(db_session).get_latest_by_asset(cash.id) is None
    assert OutlookSnapshotRepository(db_session).get_latest_by_asset(td.id) is None


def test_status_outlook_metadata(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="S", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    _seed_quotes(db_session, asset.id, [str(10 + i) for i in range(25)])
    OutlookService(db_session).run_once_for_eligible_assets()
    status = StatusService(db_session).build()
    assert status["assets_with_outlook_count"] >= 1
    assert status["last_successful_outlook_run_utc"] is not None

from app.routes.admin import run_outlook_once


def test_admin_outlook_run_once_path(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Admin", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    _seed_quotes(db_session, asset.id, [str(300 + i) for i in range(25)])
    response = run_outlook_once(db_session)
    assert response.status_code == 303
