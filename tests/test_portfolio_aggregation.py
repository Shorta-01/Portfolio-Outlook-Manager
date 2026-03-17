from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.dashboard_service import DashboardService
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService


def test_multiple_lot_aggregation(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="B", asset_type=AssetType.ETF, asset_mode=AssetMode.OWNED, quote_currency="USD"))
    ls = LotService(db_session)
    ls.create_lot(LotCreate(asset_id=asset.id, quantity="3", buy_price="5", buy_currency="USD", buy_date="2024-01-01", fees="1"))
    ls.create_lot(LotCreate(asset_id=asset.id, quantity="2", buy_price="7", buy_currency="USD", buy_date="2024-01-02", fees="1"))
    row = DashboardService(db_session).owned_rows()[0]
    assert row.quantity == Decimal("5")
    assert row.total_invested_value == Decimal("31")


def test_watchlist_separation(db_session):
    svc = InstrumentService(db_session)
    svc.create_asset(AssetCreate(display_name="Owned", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    svc.create_asset(AssetCreate(display_name="Watch", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    dash = DashboardService(db_session)
    assert len(dash.owned_rows()) == 1
    assert len(dash.watchlist_rows()) == 1
