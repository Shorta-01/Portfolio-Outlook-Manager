import json

from app.forecasting.types import ComponentContribution, EnsembleDiagnostics


def summarize_components(components: list[ComponentContribution]) -> tuple[str, str, str]:
    flags = {
        c.name: c.status == "ok"
        for c in components
    }
    detail = {
        c.name: {
            "status": c.status,
            "short": round(c.short_score, 6),
            "medium": round(c.medium_score, 6),
            "note": c.note,
        }
        for c in components
    }
    notes = [f"{c.name}:{c.note}" for c in components if c.note]
    return json.dumps(flags, sort_keys=True), json.dumps(detail, sort_keys=True), " | ".join(notes)[:512]


def build_diagnostics(
    *,
    components: list[ComponentContribution],
    disagreement_penalty: float,
    history_penalty: float,
    eval_penalty: float,
    volatility_state: str,
) -> EnsembleDiagnostics:
    return EnsembleDiagnostics(
        components_used=[c.name for c in components if c.status == "ok"],
        component_details=[
            {
                "name": c.name,
                "status": c.status,
                "short_score": round(c.short_score, 6),
                "medium_score": round(c.medium_score, 6),
                "note": c.note,
            }
            for c in components
        ],
        disagreement_penalty=round(disagreement_penalty, 6),
        history_penalty=round(history_penalty, 6),
        eval_penalty=round(eval_penalty, 6),
        volatility_state=volatility_state,
    )
