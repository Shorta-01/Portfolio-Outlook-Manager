from statistics import fmean, pstdev

from app.forecasting.smoothing import slope
from app.forecasting.types import ComponentContribution, QuotePoint


def _bound(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def smoothing_component(points: list[QuotePoint]) -> ComponentContribution:
    prices = [p.price for p in points]
    n = len(prices)
    if n < 4:
        return ComponentContribution(name="smoothing", short_score=0.0, medium_score=0.0, status="insufficient_history", note="need >=4 points")

    fast_window = min(4, n)
    slow_window = min(12, n)
    fast_avg = fmean(prices[-fast_window:])
    slow_avg = fmean(prices[-slow_window:])
    continuation = (fast_avg - slow_avg) / max(abs(slow_avg), 1e-9)
    weakening = slope(prices, min(7, n))

    short_score = _bound((continuation * 7.0) + (weakening * 2.0), -0.35, 0.35)
    medium_score = _bound((continuation * 5.0) + (weakening * 1.5), -0.28, 0.28)
    note = "continuation" if short_score >= 0 else "weakening"
    return ComponentContribution(name="smoothing", short_score=short_score, medium_score=medium_score, status="ok", note=note)


def arima_like_component(points: list[QuotePoint], enabled: bool = True) -> ComponentContribution:
    if not enabled:
        return ComponentContribution(name="arima", short_score=0.0, medium_score=0.0, status="disabled", note="component disabled")

    prices = [p.price for p in points]
    if len(prices) < 14:
        return ComponentContribution(name="arima", short_score=0.0, medium_score=0.0, status="insufficient_history", note="need >=14 points")

    try:
        returns = []
        for i in range(1, len(prices)):
            prev = prices[i - 1]
            returns.append((prices[i] - prev) / max(abs(prev), 1e-9))

        if len(returns) < 8:
            return ComponentContribution(name="arima", short_score=0.0, medium_score=0.0, status="insufficient_history", note="need >=8 returns")

        lagged = returns[:-1]
        target = returns[1:]
        denom = sum(v * v for v in lagged)
        if abs(denom) < 1e-12:
            return ComponentContribution(name="arima", short_score=0.0, medium_score=0.0, status="flat_series", note="near-zero variation")

        phi = sum(a * b for a, b in zip(lagged, target, strict=False)) / denom
        phi = _bound(phi, -1.2, 1.2)

        recent_mean = fmean(returns[-3:])
        one_step = phi * returns[-1]
        short_pred = (one_step * 0.7) + (recent_mean * 0.3)
        med_pred = (phi * one_step * 0.6) + (recent_mean * 0.4)

        scale = max(pstdev(returns[-min(20, len(returns)):]), 1e-6)
        short_score = _bound(short_pred / scale * 0.06, -0.22, 0.22)
        medium_score = _bound(med_pred / scale * 0.05, -0.18, 0.18)
        return ComponentContribution(
            name="arima",
            short_score=short_score,
            medium_score=medium_score,
            status="ok",
            note=f"ar1-lite phi={phi:.3f}",
        )
    except Exception as exc:  # noqa: BLE001
        return ComponentContribution(name="arima", short_score=0.0, medium_score=0.0, status="fit_failed", note=str(exc)[:120])
