from datetime import datetime

from app.forecasting.baseline import normalize_history
from app.forecasting.horizons import score_horizons
from app.forecasting.scoring import confidence_label, score_to_outlook, urgency_label
from app.forecasting.signals import build_signals
from app.forecasting.types import OutlookResult, QuotePoint

MODEL_VERSION = "m4-signal-ensemble-v1"


def run_ensemble(points: list[QuotePoint], now_utc: datetime) -> OutlookResult:
    normalized = normalize_history(points)
    signals = build_signals(normalized, now_utc)
    scores = score_horizons(signals)

    short_label = score_to_outlook(scores.short_term_score)
    medium_label = score_to_outlook(scores.medium_term_score)
    agreement = 1.0 - min(abs(scores.short_term_score - scores.medium_term_score), 1.0)
    confidence = confidence_label(
        agreement=agreement,
        data_sufficiency=signals.data_sufficiency,
        volatility_penalty=signals.volatility_penalty,
        freshness_penalty=signals.freshness_penalty,
    )
    if signals.data_sufficiency < 0.35:
        confidence = "low"

    distance_to_levels = 0.0
    if normalized and signals.key_level_up and signals.key_level_down:
        span = max(signals.key_level_up - signals.key_level_down, 1e-9)
        last = normalized[-1].price
        distance_up = abs(signals.key_level_up - last) / span
        distance_down = abs(last - signals.key_level_down) / span
        distance_to_levels = 1.0 - min(max(min(distance_up, distance_down), 0.0), 1.0)

    urgency = urgency_label(
        score_magnitude=min(max(abs(scores.short_term_score), abs(scores.medium_term_score)), 1.0),
        volatility_penalty=signals.volatility_penalty,
        near_key_level=distance_to_levels,
        sharp_move=min(abs(signals.momentum), 1.0),
    )

    trend_word = "positive" if signals.trend > 0.15 else "negative" if signals.trend < -0.15 else "mixed"
    mom_word = "positive" if signals.momentum > 0.15 else "negative" if signals.momentum < -0.15 else "muted"
    stretch_word = "extended" if abs(signals.mean_reversion) > 0.35 else "balanced"
    reason_summary = f"Trend is {trend_word} and momentum is {mom_word}, with price posture {stretch_word}."

    if signals.volatility_penalty > 0.65:
        risk_note = "Volatility is elevated and may invalidate directional signals quickly."
    elif signals.data_sufficiency < 0.5:
        risk_note = "History depth is limited, so conviction is intentionally reduced."
    elif signals.freshness_penalty > 0.6:
        risk_note = "Latest quote is stale, reducing reliability until fresher data arrives."
    else:
        risk_note = "Risk profile is moderate with no dominant instability signal."

    action_score = (scores.short_term_score * 0.55) + (scores.medium_term_score * 0.45)

    return OutlookResult(
        short_term_outlook=short_label,
        medium_term_outlook=medium_label,
        confidence=confidence,
        urgency=urgency,
        reason_summary=reason_summary,
        risk_note=risk_note,
        short_term_score=max(-1.0, min(1.0, scores.short_term_score)),
        medium_term_score=max(-1.0, min(1.0, scores.medium_term_score)),
        action_score=max(-1.0, min(1.0, action_score)),
        action_label="Hold",
        invalidation_note="",
        key_level_up=signals.key_level_up,
        key_level_down=signals.key_level_down,
        model_version=MODEL_VERSION,
    )
