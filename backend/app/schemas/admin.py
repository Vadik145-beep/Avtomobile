from datetime import datetime

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


class DeliveryInfo(BaseModel):
    status: str
    username: str | None
    first_name: str | None
    telegram_id: int
    opened_at: datetime | None

    model_config = {"from_attributes": True}


class LeadAdminOut(BaseModel):
    id: int
    call_id: str | None
    client_name: str | None
    country_origin: str | None
    timing: str | None
    city: str | None
    phone: str | None
    created_at: datetime
    distribution_mode: str
    is_test: bool
    deliveries: list[DeliveryInfo]

    model_config = {"from_attributes": True}


class LeadCreateIn(BaseModel):
    phone: str = Field(min_length=1)
    client_name: str | None = None
    country_origin: str | None = None
    timing: str | None = None
    city: str | None = None
    summary: str | None = None
    distribution_mode: DistributionMode = DistributionMode.coverage
    is_test: bool = False
