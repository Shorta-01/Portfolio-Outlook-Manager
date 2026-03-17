def _score_to_action(action_score: float) -> str:
    if action_score >= 0.55:
        return "Buy candidate"
    if action_score >= 0.15:
        return "Hold"
    if action_score <= -0.55:
        return "Sell candidate"
    if action_score <= -0.15:
        return "Reduce"
    return "Hold"


class ActionService:
    def map_action(self, *, action_score: float, key_level_up: float | None, key_level_down: float | None, medium_term_outlook: str) -> tuple[str, str]:
        label = _score_to_action(action_score)
        if medium_term_outlook == "bullish":
            invalidation = (
                f"A break below the lower key level ({key_level_down:.4f}) would weaken the bullish case."
                if key_level_down is not None
                else "A sustained downside break would weaken the bullish case."
            )
        elif medium_term_outlook == "bearish":
            invalidation = (
                f"A break above the upper key level ({key_level_up:.4f}) would weaken the bearish case."
                if key_level_up is not None
                else "A sustained upside break would weaken the bearish case."
            )
        else:
            invalidation = "A decisive move outside nearby key levels would break the neutral setup."
        return label, invalidation
