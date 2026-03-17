from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.outlook_evaluation import OutlookEvaluation
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.outlook_evaluation_repo import OutlookEvaluationRepository
from app.repositories.outlook_snapshot_repo import OutlookSnapshotRepository

SHORT_HORIZON_HOURS = 24
MEDIUM_HORIZON_HOURS = 24 * 7
NEUTRAL_RETURN_BAND = 0.005


@dataclass(frozen=True)
class HorizonConfig:
    horizon_type: str
    duration: timedelta
    snapshot_attr: str


HORIZONS = [
    HorizonConfig(horizon_type="short", duration=timedelta(hours=SHORT_HORIZON_HOURS), snapshot_attr="short_term_outlook"),
    HorizonConfig(horizon_type="medium", duration=timedelta(hours=MEDIUM_HORIZON_HOURS), snapshot_attr="medium_term_outlook"),
]


class OutlookEvaluationService:
    def __init__(self, db: Session):
        self.db = db
        self.quote_repo = MarketQuoteRepository(db)
        self.snapshot_repo = OutlookSnapshotRepository(db)
        self.evaluation_repo = OutlookEvaluationRepository(db)

    def _direction_from_return(self, value: float) -> str:
        if value > NEUTRAL_RETURN_BAND:
            return "bullish"
        if value < -NEUTRAL_RETURN_BAND:
            return "bearish"
        return "neutral"

    def _note_for(self, predicted: str, realized_direction: str, was_correct: bool | None) -> str:
        if was_correct is None:
            return f"neutral_band: predicted={predicted}, realized={realized_direction}"
        if was_correct:
            return f"correct: predicted={predicted}, realized={realized_direction}"
        return f"incorrect: predicted={predicted}, realized={realized_direction}"

    def _evaluate_single(self, snapshot, config: HorizonConfig, now_utc: datetime) -> OutlookEvaluation | None:
        if self.evaluation_repo.get_by_snapshot_and_horizon(snapshot.id, config.horizon_type) is not None:
            return None

        horizon_end = snapshot.timestamp_utc + config.duration
        if horizon_end > now_utc:
            return None

        start_quote = self.quote_repo.latest_at_or_before(snapshot.asset_id, snapshot.timestamp_utc)
        end_quote = self.quote_repo.earliest_at_or_after(snapshot.asset_id, horizon_end)
        if start_quote is None or end_quote is None:
            return None

        start_price = float(start_quote.price)
        end_price = float(end_quote.price)
        if start_price <= 0:
            return None

        realized_return = (end_price / start_price) - 1.0
        realized_direction = self._direction_from_return(realized_return)
        predicted = getattr(snapshot, config.snapshot_attr)

        if realized_direction == "neutral":
            was_correct = None
        else:
            was_correct = predicted == realized_direction

        evaluation = OutlookEvaluation(
            asset_id=snapshot.asset_id,
            outlook_snapshot_id=snapshot.id,
            evaluation_timestamp_utc=now_utc,
            horizon_type=config.horizon_type,
            horizon_end_timestamp_utc=horizon_end,
            predicted_label=predicted,
            realized_return=realized_return,
            realized_direction=realized_direction,
            was_correct=was_correct,
            confidence_at_prediction=snapshot.confidence,
            confidence_bucket=snapshot.confidence,
            evaluation_note=self._note_for(predicted, realized_direction, was_correct),
            model_version=snapshot.model_version,
        )
        return self.evaluation_repo.insert_evaluation(evaluation)

    def run_once(self) -> dict:
        now_utc = datetime.utcnow()
        earliest_duration = min(h.duration for h in HORIZONS)
        due_before = now_utc - earliest_duration
        evaluated = 0
        for snapshot in self.snapshot_repo.list_due_for_evaluation(due_before_utc=due_before):
            for horizon in HORIZONS:
                res = self._evaluate_single(snapshot, horizon, now_utc)
                if res is not None:
                    evaluated += 1
        self.db.commit()
        total_snapshots = self.snapshot_repo.count_rows()
        total_evaluated = self.evaluation_repo.count_rows()
        return {
            "ok": True,
            "evaluated_outlook_count": evaluated,
            "unevaluated_outlook_count": max(total_snapshots * len(HORIZONS) - total_evaluated, 0),
            "total_evaluated_rows": total_evaluated,
        }

    def scorecard_for_asset(self, asset_id: int) -> dict:
        return {
            "accuracy": self.evaluation_repo.get_aggregate_accuracy_stats(asset_id=asset_id),
            "confidence": self.evaluation_repo.get_confidence_bucket_stats(asset_id=asset_id),
            "recent": self.evaluation_repo.get_recent_by_asset(asset_id=asset_id, limit=8),
        }

    def global_scorecard(self) -> dict:
        return {
            "accuracy": self.evaluation_repo.get_aggregate_accuracy_stats(asset_id=None),
            "confidence": self.evaluation_repo.get_confidence_bucket_stats(asset_id=None),
            "total_evaluated": self.evaluation_repo.count_rows(),
            "total_outlook_snapshots": self.snapshot_repo.count_rows(),
        }
