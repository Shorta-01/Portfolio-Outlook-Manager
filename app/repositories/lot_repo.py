from datetime import date
from decimal import Decimal

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

    def find_exact_duplicate(
        self,
        *,
        asset_id: int,
        quantity: Decimal,
        buy_price: Decimal,
        buy_date: date,
        buy_currency: str,
        fees: Decimal,
        notes: str | None,
    ) -> Lot | None:
        stmt = select(Lot).where(
            Lot.asset_id == asset_id,
            Lot.quantity == quantity,
            Lot.buy_price == buy_price,
            Lot.buy_date == buy_date,
            Lot.buy_currency == buy_currency,
            Lot.fees == fees,
            Lot.notes == notes,
        )
        return self.db.execute(stmt).scalar_one_or_none()
