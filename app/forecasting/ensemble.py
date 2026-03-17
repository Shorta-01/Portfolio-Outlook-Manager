from datetime import datetime

from app.forecasting.baseline import normalize_history
from app.forecasting.classical import arima_like_component, smoothing_component
from app.forecasting.diagnostics import summarize_components
from app.forecasting.horizons import score_horizons
from app.forecasting.scoring import confidence_label, score_to_outlook, urgency_label
from app.forecasting.signals import build_signals
from app.forecasting.types import ComponentContribution, OutlookResult, QuotePoint
from app.forecasting.volatility import evaluate_volatility

MODEL_VERSION_BASELINE = "m4-signal-ensemble-v1"
MODEL_VERSION_REFINED = "m4.2-refined-ensemble-v1"


def _bound(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def run_ensemble(
    points: list[QuotePoint],
    now_utc: datetime,
    *,
    enable_classical: bool = True,
    enable_arima: bool = True,
    evaluation_quality_penalty: float = 0.0,
) -> OutlookResult:
    normalized = normalize_history(points)
    signals = build_signals(normalized, now_utc)
    baseline_scores = score_horizons(signals)

    smoothing = smoothing_component(normalized) if enable_classical else None
    arima = arima_like_component(normalized, enabled=enable_arima) if enable_classical else None
    volatility_state, instability_penalty, vol_component = evaluate_volatility(normalized)

    short_score = baseline_scores.short_term_score
    medium_score = baseline_scores.medium_term_score

    components = [
        (
            "baseline",
            _bound(baseline_scores.short_term_score, -0.75, 0.75),
            _bound(baseline_scores.medium_term_score, -0.75, 0.75),
            "ok",
            "rule_signals",
        )
    ]
    if smoothing is not None:
        short_score += smoothing.short_score
        medium_score += smoothing.medium_score
        components.append((smoothing.name, smoothing.short_score, smoothing.medium_score, smoothing.status, smoothing.note))
    if arima is not None:
        short_score += arima.short_score
        medium_score += arima.medium_score
        components.append((arima.name, arima.short_score, arima.medium_score, arima.status, arima.note))

    short_score += vol_component.short_score
    medium_score += vol_component.medium_score
    components.append((vol_component.name, vol_component.short_score, vol_component.medium_score, vol_component.status, vol_component.note))

    disagreement_penalty = 0.0
    if smoothing is not None and arima is not None and smoothing.status == "ok" and arima.status == "ok":
        disagreement_penalty = _bound(abs(smoothing.short_score - arima.short_score) * 0.7, 0.0, 0.25)

    history_penalty = _bound((1.0 - signals.data_sufficiency) * 0.35, 0.0, 0.35)
    eval_penalty = _bound(evaluation_quality_penalty, 0.0, 0.35)
    confidence_drag = disagreement_penalty + history_penalty + eval_penalty + (instability_penalty * 0.2)

    short_score = _bound(short_score)
    medium_score = _bound(medium_score)

    short_label = score_to_outlook(short_score)
    medium_label = score_to_outlook(medium_score)
    agreement = _bound(1.0 - min(abs(short_score - medium_score), 1.0), 0.0, 1.0)

    confidence = confidence_label(
        agreement=agreement,
        data_sufficiency=signals.data_sufficiency,
        volatility_penalty=_bound(max(signals.volatility_penalty, instability_penalty), 0.0, 1.0),
        freshness_penalty=signals.freshness_penalty,
        calibration_penalty=confidence_drag,
    )

    distance_to_levels = 0.0
    if normalized and signals.key_level_up and signals.key_level_down:
        span = max(signals.key_level_up - signals.key_level_down, 1e-9)
        last = normalized[-1].price
        distance_up = abs(signals.key_level_up - last) / span
        distance_down = abs(last - signals.key_level_down) / span
        distance_to_levels = 1.0 - min(max(min(distance_up, distance_down), 0.0), 1.0)

    urgency = urgency_label(
        score_magnitude=min(max(abs(short_score), abs(medium_score)), 1.0),
        volatility_penalty=max(signals.volatility_penalty, instability_penalty),
        near_key_level=distance_to_levels,
        sharp_move=min(abs(signals.momentum), 1.0),
    )

    trend_word = "positive" if signals.trend > 0.15 else "negative" if signals.trend < -0.15 else "mixed"
    mom_word = "positive" if signals.momentum > 0.15 else "negative" if signals.momentum < -0.15 else "muted"
    reason_summary = f"Trend is {trend_word}, momentum is {mom_word}, and volatility state is {volatility_state}."

    if instability_penalty > 0.65:
        risk_note = "Instability is high; confidence is reduced and signals may invalidate quickly."
    elif eval_penalty > 0.15:
        risk_note = "Recent realized hit-rate quality is soft; confidence has been recalibrated downward."
    elif signals.data_sufficiency < 0.5:
        risk_note = "History depth is limited, so conviction is intentionally reduced."
    elif signals.freshness_penalty > 0.6:
        risk_note = "Latest quote is stale, reducing reliability until fresher data arrives."
    else:
        risk_note = "Risk profile is moderate with no dominant instability signal."

    action_score = _bound((short_score * 0.55) + (medium_score * 0.45))

    serialized_components = [
        ComponentContribution(name=c[0], short_score=c[1], medium_score=c[2], status=c[3], note=c[4])
        for c in components
    ]
    flags_json, summary_json, diag_note = summarize_components(serialized_components)

    return OutlookResult(
        short_term_outlook=short_label,
        medium_term_outlook=medium_label,
        confidence=confidence,
        urgency=urgency,
        reason_summary=reason_summary,
        risk_note=risk_note,
        short_term_score=short_score,
        medium_term_score=medium_score,
        action_score=action_score,
        action_label="Hold",
        invalidation_note="",
        key_level_up=signals.key_level_up,
        key_level_down=signals.key_level_down,
        model_version=MODEL_VERSION_REFINED if enable_classical else MODEL_VERSION_BASELINE,
        component_flags=flags_json,
        component_summary=summary_json,
        model_diagnostic_note=diag_note,
        volatility_state=volatility_state,
    )
