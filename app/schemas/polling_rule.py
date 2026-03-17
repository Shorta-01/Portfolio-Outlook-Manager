from pydantic import BaseModel, Field


class PollingRuleCreate(BaseModel):
    asset_id: int
    poll_every_minutes: int = Field(gt=0)
    market_hours_only: bool = False
    enabled: bool = True
