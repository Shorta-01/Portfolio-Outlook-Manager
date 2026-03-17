from datetime import datetime
from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.models.market_quote import MarketQuote
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService
from app.services.status_service import StatusService


def test_status_service(db_session):
    InstrumentService(db_session).create_asset(AssetCreate(display_name="X", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR", current_amount="1"))
    status = StatusService(db_session).build()
    assert status["database_reachable"] is True
    assert status["asset_counts"][AssetMode.CASH.value] == 1
    assert status["assets_without_quote_data"] == 0
    assert status["base_currency"] == "EUR"


def test_status_reports_missing_quote_and_fx_counts(db_session):
    with_quote = InstrumentService(db_session).create_asset(AssetCreate(display_name="Q", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    missing_fx = InstrumentService(db_session).create_asset(AssetCreate(display_name="FX", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="USD"))
    missing_quote = InstrumentService(db_session).create_asset(AssetCreate(display_name="NQ", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=with_quote.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    LotService(db_session).create_lot(LotCreate(asset_id=missing_fx.id, quantity="1", buy_price="10", buy_currency="USD", buy_date="2024-01-01"))
    LotService(db_session).create_lot(LotCreate(asset_id=missing_quote.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    db_session.add(MarketQuote(asset_id=with_quote.id, provider_name="manual", price=Decimal("11"), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.add(MarketQuote(asset_id=missing_fx.id, provider_name="manual", price=Decimal("11"), quote_currency="USD", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.commit()

    status = StatusService(db_session).build()
    assert status["assets_with_latest_quote"] == 2
    assert status["assets_without_quote_data"] == 1
    assert status["assets_missing_fx_for_base_valuation"] == 1
    assert status["totals_complete"] is False
    assert status["missing_fx_asset_count"] == 1
    assert status["missing_quote_asset_count"] == 1
