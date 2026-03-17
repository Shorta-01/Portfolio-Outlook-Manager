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
class ComponentContribution:
    name: str
    short_score: float
    medium_score: float
    status: str
    note: str = ""


@dataclass(frozen=True)
class EnsembleDiagnostics:
    components_used: list[str]
    component_details: list[dict[str, str | float | bool | None]]
    disagreement_penalty: float
    history_penalty: float
    eval_penalty: float
    volatility_state: str


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
    component_flags: str
    component_summary: str
    model_diagnostic_note: str
    volatility_state: str
