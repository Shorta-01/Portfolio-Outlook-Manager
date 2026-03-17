from statistics import fmean, pstdev

from app.forecasting.types import ComponentContribution, QuotePoint


def _bound(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def evaluate_volatility(points: list[QuotePoint]) -> tuple[str, float, ComponentContribution]:
    prices = [p.price for p in points]
    if len(prices) < 6:
        return "unknown", 0.25, ComponentContribution(name="volatility", short_score=-0.05, medium_score=-0.04, status="insufficient_history", note="need >=6 points")

    returns = []
    abs_ranges = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        ret = (prices[i] - prev) / max(abs(prev), 1e-9)
        returns.append(ret)
        abs_ranges.append(abs(ret))

    recent_returns = returns[-min(20, len(returns)):]
    vol = pstdev(recent_returns) if len(recent_returns) > 1 else 0.0
    avg_abs = fmean(abs_ranges[-min(20, len(abs_ranges)):]) if abs_ranges else 0.0
    instability_penalty = _bound((vol * 16.0) + (avg_abs * 10.0), 0.0, 1.0)

    if instability_penalty >= 0.65:
        state = "high"
    elif instability_penalty >= 0.35:
        state = "moderate"
    else:
        state = "low"

    contribution = ComponentContribution(
        name="volatility",
        short_score=_bound(-instability_penalty * 0.22, -0.25, 0.0),
        medium_score=_bound(-instability_penalty * 0.18, -0.22, 0.0),
        status="ok",
        note=f"instability={instability_penalty:.3f}",
    )
    return state, instability_penalty, contribution
