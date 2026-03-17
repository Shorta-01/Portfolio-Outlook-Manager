from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lot import Lot


class LotRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, lot: Lot) -> Lot:
        self.db.add(lot)
        self.db.flush()
        return lot

    def list_for_asset(self, asset_id: int) -> list[Lot]:
        stmt = select(Lot).where(Lot.asset_id == asset_id).order_by(Lot.buy_date.desc())
        return list(self.db.execute(stmt).scalars().all())
