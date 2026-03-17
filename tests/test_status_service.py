from app.models.asset import AssetMode, AssetType
from app.schemas.asset import AssetCreate
from app.services.instrument_service import InstrumentService
from app.services.status_service import StatusService


def test_status_service(db_session):
    InstrumentService(db_session).create_asset(AssetCreate(display_name="X", asset_type=AssetType.CASH, asset_mode=AssetMode.CASH, quote_currency="EUR"))
    status = StatusService(db_session).build()
    assert status["database_reachable"] is True
    assert status["asset_counts"][AssetMode.CASH.value] == 1
    assert status["totals_complete"] is True
    assert status["missing_fx_asset_count"] == 0
    assert status["missing_quote_asset_count"] == 0
