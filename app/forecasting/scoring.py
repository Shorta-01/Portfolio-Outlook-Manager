
def score_to_outlook(value: float) -> str:
    if value >= 0.2:
        return "bullish"
    if value <= -0.2:
        return "bearish"
    return "neutral"


def confidence_label(
    *,
    agreement: float,
    data_sufficiency: float,
    volatility_penalty: float,
    freshness_penalty: float,
    calibration_penalty: float = 0.0,
) -> str:
    raw = (agreement * 0.4) + (data_sufficiency * 0.35) + ((1.0 - volatility_penalty) * 0.15) + ((1.0 - freshness_penalty) * 0.10)
    adjusted = raw - calibration_penalty
    if adjusted >= 0.7:
        return "high"
    if adjusted >= 0.45:
        return "medium"
    return "low"


def urgency_label(*, score_magnitude: float, volatility_penalty: float, near_key_level: float, sharp_move: float) -> str:
    raw = (score_magnitude * 0.4) + (volatility_penalty * 0.2) + (near_key_level * 0.2) + (sharp_move * 0.2)
    if raw >= 0.7:
        return "high"
    if raw >= 0.4:
        return "medium"
    return "low"
