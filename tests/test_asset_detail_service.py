from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.models.market_quote import MarketQuote
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.asset_detail_service import AssetDetailService
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService


def test_asset_detail_owned_market_asset(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Asset", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    db_session.add(MarketQuote(asset_id=asset.id, provider_name="seed", price=Decimal("15"), quote_currency="EUR", provider_timestamp_utc=datetime.utcnow(), freshness_status="unknown", interval_type="spot", is_backfill=False))
    db_session.commit()

    model = AssetDetailService(db_session).build(asset.id)
    assert model["is_owned"] is True
    assert len(model["lots"]) == 1
    assert model["aggregate"].value_now == Decimal("15")
    assert model["aggregate"].valuation_warning is None


def test_asset_detail_owned_market_asset_missing_quote_warning(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="NoQuote", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    model = AssetDetailService(db_session).build(asset.id)
    assert model["aggregate"].has_quote is False
    assert model["aggregate"].valuation_warning == "Quote unavailable"


def test_asset_detail_watchlist_asset(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Watch", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    model = AssetDetailService(db_session).build(asset.id)
    assert model["is_watchlist"] is True
    assert model["aggregate"] is None


def test_asset_detail_cash_asset(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Cash", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR", current_amount="100"))
    model = AssetDetailService(db_session).build(asset.id)
    assert model["is_cash"] is True
    assert model["valuation"].value_now_base_currency == Decimal("100")


def test_asset_detail_term_deposit_asset(db_session):
    asset = InstrumentService(db_session).create_asset(
        AssetCreate(
            display_name="TD",
            asset_type=AssetType.TERM_DEPOSIT,
            asset_mode=AssetMode.TERM_DEPOSIT,
            quote_currency="EUR",
            principal_amount="1000",
            interest_rate_annual="0.05",
            start_date=date.today() - timedelta(days=50),
            maturity_date=date.today() + timedelta(days=50),
        )
    )
    model = AssetDetailService(db_session).build(asset.id)
    assert model["is_term_deposit"] is True
    assert model["valuation"].value_now_base_currency > Decimal("1000")


import pytest
from pydantic import ValidationError


def test_reject_negative_quantity_price(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Asset2", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    with pytest.raises(ValidationError):
        LotCreate(asset_id=asset.id, quantity="-1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01")


def test_lot_rejected_for_watchlist(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Watch", asset_type=AssetType.STOCK, asset_mode=AssetMode.WATCHLIST, quote_currency="EUR"))
    with pytest.raises(ValueError):
        LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
