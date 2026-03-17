from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetMode


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, asset: Asset) -> Asset:
        self.db.add(asset)
        self.db.flush()
        return asset

    def get(self, asset_id: int) -> Asset | None:
        return self.db.get(Asset, asset_id)

    def find_by_name_mode(self, display_name: str, mode: AssetMode) -> Asset | None:
        stmt = select(Asset).where(Asset.display_name == display_name, Asset.asset_mode == mode)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_mode(self, mode: AssetMode) -> list[Asset]:
        stmt = select(Asset).where(Asset.asset_mode == mode, Asset.enabled.is_(True)).order_by(Asset.display_name)
        return list(self.db.execute(stmt).scalars().all())

    def count_by_mode(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for mode in AssetMode:
            result[mode.value] = len(self.list_by_mode(mode))
        return result
