def simple_moving_average(values: list[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    return sum(values[-window:]) / window


def slope(values: list[float], window: int) -> float:
    if len(values) < max(window, 2):
        return 0.0
    sample = values[-window:]
    return (sample[-1] - sample[0]) / max(abs(sample[0]), 1e-9)
