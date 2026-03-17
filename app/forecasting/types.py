from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class QuotePoint:
    timestamp_utc: datetime
    price: float


@dataclass(frozen=True)
class SignalBundle:
    trend: float
    momentum: float
    mean_reversion: float
    volatility_penalty: float
    key_level_up: float | None
    key_level_down: float | None
    data_sufficiency: float
    freshness_penalty: float


@dataclass(frozen=True)
class HorizonScores:
    short_term_score: float
    medium_term_score: float


@dataclass(frozen=True)
class OutlookResult:
    short_term_outlook: str
    medium_term_outlook: str
    confidence: str
    urgency: str
    reason_summary: str
    risk_note: str
    short_term_score: float
    medium_term_score: float
    action_score: float
    action_label: str
    invalidation_note: str
    key_level_up: float | None
    key_level_down: float | None
    model_version: str
