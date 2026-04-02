from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass
class UserInfo:
    telegram_id: int
    username: str | None
    first_name: str | None
    limit_count: int


@dataclass
class OpenContactResult:
    phone: str
    lead_id: int


@dataclass
class IcebreakerResult:
    dispatched: int
    balance_empty: bool


class BackendClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.backend_url,
            headers={"Authorization": f"Bearer {settings.bot_internal_secret}"},
            timeout=10.0,
        )

    async def register_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> UserInfo:
        resp = await self._client.post(
            "/api/bot/register",
            json={
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return UserInfo(
            telegram_id=data["telegram_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            limit_count=data["limit_count"],
        )

    async def get_user(self, tg_id: int) -> UserInfo | None:
        resp = await self._client.get(f"/api/bot/user/{tg_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return UserInfo(
            telegram_id=data["telegram_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            limit_count=data["limit_count"],
        )

    async def icebreaker(self, telegram_id: int) -> IcebreakerResult:
        resp = await self._client.post(
            "/api/bot/icebreaker",
            json={"telegram_id": telegram_id},
        )
        resp.raise_for_status()
        data = resp.json()
        return IcebreakerResult(
            dispatched=data["dispatched"],
            balance_empty=data.get("balance_empty", False),
        )

    async def open_contact(
        self, telegram_id: int, lead_id: int, delivery_id: int
    ) -> OpenContactResult:
        resp = await self._client.post(
            "/api/bot/open-contact",
            json={
                "telegram_id": telegram_id,
                "lead_id": lead_id,
                "delivery_id": delivery_id,
            },
        )
        if resp.status_code in (402, 409):
            resp.raise_for_status()
        resp.raise_for_status()
        data = resp.json()
        return OpenContactResult(phone=data["phone"], lead_id=data["lead_id"])

    async def aclose(self) -> None:
        await self._client.aclose()


client = BackendClient()
