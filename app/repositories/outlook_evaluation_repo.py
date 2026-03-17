from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.outlook_evaluation import OutlookEvaluation


class OutlookEvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def insert_evaluation(self, evaluation: OutlookEvaluation) -> OutlookEvaluation:
        self.db.add(evaluation)
        self.db.flush()
        return evaluation

    def get_by_snapshot_and_horizon(self, outlook_snapshot_id: int, horizon_type: str) -> OutlookEvaluation | None:
        stmt = select(OutlookEvaluation).where(
            OutlookEvaluation.outlook_snapshot_id == outlook_snapshot_id,
            OutlookEvaluation.horizon_type == horizon_type,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_recent_by_asset(self, asset_id: int, limit: int = 20) -> list[OutlookEvaluation]:
        stmt = (
            select(OutlookEvaluation)
            .where(OutlookEvaluation.asset_id == asset_id)
            .order_by(OutlookEvaluation.evaluation_timestamp_utc.desc(), OutlookEvaluation.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_aggregate_accuracy_stats(self, asset_id: int | None = None) -> dict[str, dict[str, int | float | None]]:
        data: dict[str, dict[str, int | float | None]] = {}
        for horizon in ("short", "medium"):
            stmt = select(OutlookEvaluation.was_correct).where(OutlookEvaluation.horizon_type == horizon)
            if asset_id is not None:
                stmt = stmt.where(OutlookEvaluation.asset_id == asset_id)
            values = list(self.db.execute(stmt).scalars().all())
            judged = [v for v in values if v is not None]
            hits = sum(1 for v in judged if v)
            total = len(judged)
            neutral = len(values) - total
            data[horizon] = {
                "hit_rate": (hits / total) if total else None,
                "hits": hits,
                "total": total,
                "neutral_count": neutral,
            }
        return data

    def get_confidence_bucket_stats(self, asset_id: int | None = None) -> list[dict]:
        stmt = (
            select(
                OutlookEvaluation.confidence_bucket,
                func.count(OutlookEvaluation.id),
                func.sum(case((OutlookEvaluation.was_correct.is_(True), 1), else_=0)),
                func.sum(case((OutlookEvaluation.was_correct.is_(None), 1), else_=0)),
            )
            .group_by(OutlookEvaluation.confidence_bucket)
            .order_by(OutlookEvaluation.confidence_bucket.asc())
        )
        if asset_id is not None:
            stmt = stmt.where(OutlookEvaluation.asset_id == asset_id)

        rows = self.db.execute(stmt).all()
        out = []
        for bucket, total, hits, neutral in rows:
            judged = int(total or 0) - int(neutral or 0)
            hit_rate = (int(hits or 0) / judged) if judged else None
            out.append(
                {
                    "confidence_bucket": bucket,
                    "total": int(total or 0),
                    "hits": int(hits or 0),
                    "neutral": int(neutral or 0),
                    "judged_total": judged,
                    "hit_rate": hit_rate,
                }
            )
        return out

    def count_rows(self) -> int:
        return len(self.db.execute(select(OutlookEvaluation.id)).scalars().all())
