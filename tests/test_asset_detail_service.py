from app.models.asset import AssetMode, AssetType
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.asset_detail_service import AssetDetailService
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService


def test_asset_detail_returns_lots(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="Asset", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    LotService(db_session).create_lot(LotCreate(asset_id=asset.id, quantity="1", buy_price="10", buy_currency="EUR", buy_date="2024-01-01"))
    model = AssetDetailService(db_session).build(asset.id)
    assert model["is_owned"] is True
    assert len(model["lots"]) == 1

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
