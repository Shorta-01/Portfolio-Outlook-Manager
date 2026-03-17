from datetime import datetime
from statistics import pstdev

from app.forecasting.smoothing import simple_moving_average, slope
from app.forecasting.types import QuotePoint, SignalBundle


def _bound(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def build_signals(points: list[QuotePoint], now_utc: datetime) -> SignalBundle:
    prices = [p.price for p in points]
    n = len(prices)
    if n == 0:
        return SignalBundle(0.0, 0.0, 0.0, 1.0, None, None, 0.0, 1.0)

    short_ma = simple_moving_average(prices, min(5, n)) or prices[-1]
    long_window = min(20, n)
    long_ma = simple_moving_average(prices, long_window) or prices[-1]
    trend = _bound((short_ma - long_ma) / max(abs(long_ma), 1e-9) * 5.0)

    ret_3 = 0.0 if n < 4 else (prices[-1] - prices[-4]) / max(abs(prices[-4]), 1e-9)
    recent_slope = slope(prices, min(7, n))
    momentum = _bound((ret_3 * 4.0) + (recent_slope * 2.0))

    stdev = pstdev(prices[-min(20, n) :]) if n > 1 else 0.0
    stretch = 0.0 if stdev == 0 else (prices[-1] - long_ma) / stdev
    mean_reversion = _bound(-stretch / 3.0)

    returns = []
    for i in range(1, n):
        prev = prices[i - 1]
        returns.append((prices[i] - prev) / max(abs(prev), 1e-9))
    vol = pstdev(returns[-min(20, len(returns)) :]) if len(returns) > 1 else 0.0
    volatility_penalty = _bound(vol * 20.0, 0.0, 1.0)

    key_up = max(prices[-min(20, n) :]) if n >= 2 else prices[-1]
    key_down = min(prices[-min(20, n) :]) if n >= 2 else prices[-1]

    data_sufficiency = min(1.0, n / 20.0)
    age_hours = max((now_utc - points[-1].timestamp_utc).total_seconds() / 3600.0, 0.0)
    freshness_penalty = _bound(age_hours / 48.0, 0.0, 1.0)

    return SignalBundle(
        trend=trend,
        momentum=momentum,
        mean_reversion=mean_reversion,
        volatility_penalty=volatility_penalty,
        key_level_up=key_up,
        key_level_down=key_down,
        data_sufficiency=data_sufficiency,
        freshness_penalty=freshness_penalty,
    )
