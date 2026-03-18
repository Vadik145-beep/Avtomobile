from pydantic import BaseModel, Field

from app.models.lead import DistributionMode


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BonusIn(BaseModel):
    amount: int = Field(gt=0)
    comment: str = Field(min_length=1)


class SettingsIn(BaseModel):
    mode: DistributionMode
    speed_group_size: int = Field(default=5, ge=1, le=100)


class SettingsOut(BaseModel):
    mode: DistributionMode
    speed_group_size: int
    updated_by: int | None

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    users_total: int
    leads_today: int
    leads_week: int
    leads_month: int
