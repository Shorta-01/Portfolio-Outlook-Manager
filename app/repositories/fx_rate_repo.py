from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fx_rate import FXRate


class FXRateRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, fx_rate: FXRate) -> FXRate:
        self.db.add(fx_rate)
        self.db.flush()
        return fx_rate

    def latest_for_pair(self, pair_code: str) -> FXRate | None:
        stmt = (
            select(FXRate)
            .where(FXRate.pair_code == pair_code)
            .order_by(FXRate.provider_timestamp_utc.desc(), FXRate.ingested_at_utc.desc(), FXRate.id.desc())
        )
        return self.db.execute(stmt).scalars().first()
