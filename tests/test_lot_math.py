from decimal import Decimal

from app.models.asset import AssetMode, AssetType
from app.schemas.asset import AssetCreate
from app.schemas.lot import LotCreate
from app.services.instrument_service import InstrumentService
from app.services.lot_service import LotService
from app.services.portfolio_service import PortfolioService
from app.repositories.lot_repo import LotRepository


def test_weighted_average_buy_price(db_session):
    asset = InstrumentService(db_session).create_asset(AssetCreate(display_name="A", asset_type=AssetType.STOCK, asset_mode=AssetMode.OWNED, quote_currency="EUR"))
    lot_service = LotService(db_session)
    lot_service.create_lot(LotCreate(asset_id=asset.id, quantity=Decimal("2"), buy_price=Decimal("10"), buy_currency="EUR", buy_date="2024-01-01"))
    lot_service.create_lot(LotCreate(asset_id=asset.id, quantity=Decimal("1"), buy_price=Decimal("20"), buy_currency="EUR", buy_date="2024-01-02"))
    row = PortfolioService(LotRepository(db_session)).aggregate_asset(asset)
    assert row.weighted_avg_buy_price_ex_fees == Decimal("13.33333333333333333333333333")
