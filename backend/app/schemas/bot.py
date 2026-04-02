from pydantic import BaseModel


class OpenContactIn(BaseModel):
    telegram_id: int
    lead_id: int
    delivery_id: int | None = None


class OpenContactOut(BaseModel):
    phone: str
    lead_id: int


class ErrorOut(BaseModel):
    detail: str


class MiniAppUserOut(BaseModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    limit_count: int


class MiniAppBuyIn(BaseModel):
    package_id: str   # "10" | "50" | "100"
    amount: int       # number of limits (must match package)


class MiniAppBuyOut(BaseModel):
    status: str              # "created" | "error"
    payment_id: str | None
    invoice_url: str | None
    message: str


class IcebreakerIn(BaseModel):
    telegram_id: int


class IcebreakerOut(BaseModel):
    dispatched: int
