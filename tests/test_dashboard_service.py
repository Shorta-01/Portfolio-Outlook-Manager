from app.services.dashboard_service import DashboardService
from datetime import datetime
from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.models.market_quote import MarketQuote
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService


def test_dashboard_empty(db_session):
    svc = DashboardService(db_session)
    assert svc.owned_rows() == []
    assert svc.watchlist_rows() == []
    summary = svc.summary_cards()
    assert summary.total_invested == 0
    assert summary.total_current_value == 0


def test_dashboard_totals_exclude_assets_without_base_valuation(db_session):
    eur = InstrumentService(db_session).create_asset(AssetCreate(display_name="EUR", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    usd_missing_fx = InstrumentService(db_session).create_asset(AssetCreate(display_name="USD", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="USD"))
    missing_quote = InstrumentService(db_session).create_asset(AssetCreate(display_name="NoQuote", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=eur.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    LotService(db_session).create_lot(LotCreate(asset_id=usd_missing_fx.id, quantity="1", buy_price="20", buy_currency="USD", buy_date="2024-01-01"))
    LotService(db_session).create_lot(LotCreate(asset_id=missing_quote.id, quantity="1", buy_price="30", buy_currency="EUR", buy_date="2024-01-01"))
    db_session.add(MarketQuote(asset_id=eur.id, provider_name="seed", price=Decimal("11"), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.add(MarketQuote(asset_id=usd_missing_fx.id, provider_name="seed", price=Decimal("25"), quote_currency="USD", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.commit()

    summary = DashboardService(db_session).summary_cards()
    assert summary.total_invested == Decimal("60")
    assert summary.total_current_value == Decimal("11")
    assert summary.totals_complete is False
    assert summary.missing_fx_asset_count == 1
    assert summary.missing_quote_asset_count == 1
    assert summary.omitted_from_totals_count == 2
