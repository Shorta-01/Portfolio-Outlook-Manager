from app.forecasting.types import HorizonScores, SignalBundle


def score_horizons(signals: SignalBundle) -> HorizonScores:
    short_term = (signals.trend * 0.35) + (signals.momentum * 0.45) + (signals.mean_reversion * 0.20)
    medium_term = (signals.trend * 0.55) + (signals.momentum * 0.25) + (signals.mean_reversion * 0.20)
    risk_drag = signals.volatility_penalty * 0.30
    return HorizonScores(short_term_score=short_term - risk_drag, medium_term_score=medium_term - (risk_drag * 0.8))
