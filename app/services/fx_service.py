from decimal import Decimal

from app.repositories.fx_rate_repo import FXRateRepository


class FXService:
    def __init__(self, fx_repo: FXRateRepository):
        self.fx_repo = fx_repo

    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal | None:
        from_ccy = from_currency.upper()
        to_ccy = to_currency.upper()
        if from_ccy == to_ccy:
            return amount
        pair = f"{from_ccy}/{to_ccy}"
        latest = self.fx_repo.latest_for_pair(pair)
        if latest is not None:
            return amount * latest.rate
        inverse = self.fx_repo.latest_for_pair(f"{to_ccy}/{from_ccy}")
        if inverse is not None and inverse.rate != 0:
            return amount / inverse.rate
        return None
