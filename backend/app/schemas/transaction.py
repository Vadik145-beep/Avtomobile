from datetime import datetime

from pydantic import BaseModel

from app.models.transaction import TransactionType


class TransactionOut(BaseModel):
    id: int
    user_id: int
    type: TransactionType
    amount: int
    comment: str | None
    source: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
