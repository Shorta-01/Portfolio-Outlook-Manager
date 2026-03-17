from datetime import datetime
from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.models.market_quote import MarketQuote
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.dashboard_service import DashboardService
from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService


def _seed_owned(db_session):
    a1 = InstrumentService(db_session).create_asset(AssetCreate(display_name="Alpha", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR", isin="ISIN-A"))
    a2 = InstrumentService(db_session).create_asset(AssetCreate(display_name="Beta", asset_type=AssetType.ETF, asset_mode=AssetMode.OWNED, quote_currency="USD", isin="ISIN-B"))
    LotService(db_session).create_lot(LotCreate(asset_id=a1.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    LotService(db_session).create_lot(LotCreate(asset_id=a2.id, quantity="1", buy_price="10", buy_currency="USD", buy_date="2024-01-01"))
    db_session.add(MarketQuote(asset_id=a1.id, provider_name="seed", price=Decimal("11"), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.commit()


def test_dashboard_query_filter_search_sort(db_session):
    _seed_owned(db_session)
    svc = DashboardService(db_session)
    rows = svc.query_owned_rows({"q": "isin-a", "sort": "asset_name", "dir": "asc", "asset_type": "", "currency": "", "outlook": "", "action": "", "freshness": "", "source": "", "incomplete_only": "0"})
    assert len(rows) == 1
    assert rows[0].asset_name == "Alpha"
    incomplete = svc.query_owned_rows({"q": "", "sort": "asset_name", "dir": "asc", "asset_type": "", "currency": "", "outlook": "", "action": "", "freshness": "", "source": "", "incomplete_only": "1"})
    assert len(incomplete) == 1
    assert incomplete[0].asset_name == "Beta"


def test_watchlist_query_filter_search(db_session):
    InstrumentService(db_session).create_asset(AssetCreate(display_name="Watch A", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", isin="WA"))
    InstrumentService(db_session).create_asset(AssetCreate(display_name="Watch B", asset_type=AssetType.ETF, asset_mode=AssetMode.WATCHLIST, quote_currency="USD", isin="WB"))
    svc = DashboardService(db_session)
    rows = svc.query_watchlist_rows({"q": "wb", "sort": "display_name", "dir": "asc", "asset_type": "", "currency": "", "outlook": "", "action": "", "freshness": "", "source": ""})
    assert len(rows) == 1
    assert rows[0]["display_name"] == "Watch B"


def test_export_service_shapes(db_session):
    _seed_owned(db_session)
    InstrumentService(db_session).create_asset(AssetCreate(display_name="Watch A", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR", isin="WA"))
    exports = ExportService(db_session)
    assert "asset_id,asset_name" in exports.portfolio_csv()
    assert "asset_id,display_name" in exports.watchlist_csv()
    assert "asset_id,asset_name,quantity" in exports.lots_csv()


def test_watchlist_promote_to_owned(db_session):
    watch = InstrumentService(db_session).create_asset(AssetCreate(display_name="W", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    promoted = InstrumentService(db_session).promote_watchlist_to_owned(watch.id)
    assert promoted.asset_mode == AssetMode.OWNED


def test_import_friendly_error_message(db_session):
    result = ImportService(db_session).import_csv("display_name,asset_type,quote_currency\nBad,not_real,EUR\n", "watchlist")
    assert len(result.failed_rows) == 1
    assert "Invalid asset type" in result.failed_rows[0].message
