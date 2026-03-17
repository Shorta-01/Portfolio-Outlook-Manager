from sqlalchemy.orm import Session

from app.models.asset import AssetMode
from app.models.lot import Lot
from app.repositories.asset_repo import AssetRepository
from app.repositories.lot_repo import LotRepository
from app.schemas.lot import LotCreate


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
