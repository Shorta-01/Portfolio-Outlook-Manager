from app.forecasting.types import QuotePoint


def normalize_history(points: list[QuotePoint]) -> list[QuotePoint]:
    """Sort and drop non-positive prices for deterministic signal inputs."""
    cleaned = [p for p in points if p.price > 0]
    return sorted(cleaned, key=lambda p: p.timestamp_utc)
