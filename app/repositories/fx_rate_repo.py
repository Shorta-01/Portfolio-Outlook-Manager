from datetime import datetime
from decimal import Decimal

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

    def find_duplicate(
        self,
        *,
        pair_code: str,
        provider_name: str,
        provider_timestamp_utc: datetime,
        rate: Decimal,
        interval_type: str,
    ) -> FXRate | None:
        stmt = select(FXRate).where(
            FXRate.pair_code == pair_code,
            FXRate.provider_name == provider_name,
            FXRate.provider_timestamp_utc == provider_timestamp_utc,
            FXRate.rate == rate,
            FXRate.interval_type == interval_type,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def count_rows(self) -> int:
        return len(self.db.execute(select(FXRate.id)).scalars().all())
