from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.models.lot import Lot
from app.repositories.asset_repo import AssetRepository
from app.repositories.lot_repo import LotRepository
from app.schemas.lot import LotCreate
from app.schemas.lot import LotUpdate


class LotService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.lot_repo = LotRepository(db)

    def create_lot(self, payload: LotCreate) -> Lot:
        asset = self.asset_repo.get(payload.asset_id)
        if asset is None:
            raise ValueError("Asset does not exist")
        if asset.asset_mode != AssetMode.OWNED:
            raise ValueError("Lots can only be created for owned assets")
        lot = Lot(**payload.model_dump())
        self.lot_repo.add(lot)
        self.db.commit()
        self.db.refresh(lot)
        return lot

    def list_lots_for_asset(self, asset_id: int) -> list[Lot]:
        return self.lot_repo.list_for_asset(asset_id)

    def update_lot(self, lot_id: int, payload: LotUpdate) -> Lot:
        lot = self.lot_repo.get(lot_id)
        if lot is None:
            raise ValueError("Lot not found")
        lot.quantity = payload.quantity
        lot.buy_price = payload.buy_price
        lot.buy_currency = payload.buy_currency.strip().upper()
        lot.buy_date = payload.buy_date
        lot.fees = payload.fees
        lot.notes = payload.notes
        self.db.commit()
        self.db.refresh(lot)
        return lot

    def delete_lot(self, lot_id: int) -> int:
        lot = self.lot_repo.get(lot_id)
        if lot is None:
            raise ValueError("Lot not found")
        asset_id = lot.asset_id
        self.lot_repo.delete(lot)
        self.db.commit()
        return asset_id
