from datetime import datetime

from pydantic import BaseModel, Field


class LidozvonWebhookIn(BaseModel):
    """Входящий payload от Лидозвон согласно CLIENT_WEBHOOK_SYSADMIN_SPEC v1.0."""

    call_id: str
    assistant_name: str | None = None
    direction: str | None = None
    phone: str | None = None
    duration_seconds: int | None = None
    ended_reason: str | None = None
    ended_at: datetime | None = None
    transcript: str | None = None
    recording_url: str = ""
    structured_data: dict = Field(default_factory=dict)
    is_qualified: bool | None = None
    qualification_reason: str | None = None
    test: bool | None = Field(default=None, alias="_test")

    model_config = {"populate_by_name": True}


class LeadOut(BaseModel):
    id: int
    client_name: str | None
    country_origin: str | None
    timing: str | None
    city: str | None
    summary: str | None
    recording_url: str | None
    agreements: str | None
    about_client: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadCardOut(BaseModel):
    """Карточка лида для бота — без телефона."""
    id: int
    client_name: str | None
    country_origin: str | None
    timing: str | None
    city: str | None
    summary: str | None
    recording_url: str | None
    agreements: str | None
    about_client: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
