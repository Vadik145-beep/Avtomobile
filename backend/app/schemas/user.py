from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None


class UserOut(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    limit_count: int
    is_active: bool
    icebreaker_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
