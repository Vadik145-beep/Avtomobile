import hashlib
import hmac
import json
import logging
import urllib.parse

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.credit import credit_limits
from app.core.debit import open_contact
from app.core.distributor import deliver_queued_leads_to_user, enqueue_user
from app.models.distribution_setting import DistributionSetting, LeadDeliveryMode
from app.core.security import verify_bot_secret
from app.database import get_db
from app.dependencies import get_redis
from app.models.user import User
from app.payments.factory import get_provider
from app.payments.packages import PACKAGES
from app.schemas.bot import (
    IcebreakerIn,
    IcebreakerOut,
    MiniAppBuyIn,
    MiniAppBuyOut,
    MiniAppUserOut,
    OpenContactIn,
    OpenContactOut,
    StopIcebreakerIn,
)
from app.schemas.user import UserCreate, UserOut

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/bot",
    tags=["bot"],
    dependencies=[Depends(verify_bot_secret)],
)

miniapp_router = APIRouter(
    prefix="/api/bot/miniapp",
    tags=["miniapp"],
)


# ── Mini App initData validation ────────────────────────────────────────────

def _validate_init_data(init_data: str) -> dict:
    """
    Validates Telegram WebApp initData using HMAC-SHA256.
    Returns parsed user dict on success, raises 403 on failure.
    """
    if not init_data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing initData")

    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)

    if not received_hash:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid initData")

    user_json = parsed.get("user", "{}")
    try:
        return json.loads(user_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user data"
        ) from exc


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Зарегистрировать или обновить пользователя",
)
async def register_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> UserOut:
    result = await db.execute(select(User).where(User.telegram_id == body.telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=body.telegram_id,
            username=body.username,
            first_name=body.first_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        # Добавляем нового пользователя в очередь exclusive-режима
        await enqueue_user(body.telegram_id, redis)
    else:
        # Update mutable fields if provided
        changed = False
        if body.username is not None and user.username != body.username:
            user.username = body.username
            changed = True
        if body.first_name is not None and user.first_name != body.first_name:
            user.first_name = body.first_name
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)

    return UserOut.model_validate(user)


@router.get(
    "/user/{tg_id}",
    response_model=UserOut,
    summary="Получить пользователя по telegram_id",
)
async def get_user(tg_id: int, db: AsyncSession = Depends(get_db)) -> UserOut:
    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    return UserOut.model_validate(user)


@router.post(
    "/open-contact",
    response_model=OpenContactOut,
    summary="Атомарное открытие контакта (списание лимита)",
)
async def bot_open_contact(
    body: OpenContactIn,
    db: AsyncSession = Depends(get_db),
) -> OpenContactOut:
    phone, recording_url = await open_contact(body.telegram_id, body.lead_id, db)
    return OpenContactOut(phone=phone, lead_id=body.lead_id, recording_url=recording_url)


@router.post(
    "/icebreaker",
    response_model=IcebreakerOut,
    summary="Запустить ледокол — активировать получение лидов",
)
async def bot_icebreaker(
    body: IcebreakerIn,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> IcebreakerOut:
    user_result = await db.execute(
        select(User).where(User.telegram_id == body.telegram_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

    if user.limit_count <= 0:
        return IcebreakerOut(dispatched=0, balance_empty=True)

    # Mark icebreaker as active so new incoming leads are delivered in real-time
    if not user.icebreaker_active:
        user.icebreaker_active = True

    # Determine current distribution mode
    settings_result = await db.execute(select(DistributionSetting).limit(1))
    dist_settings = settings_result.scalar_one_or_none()
    mode = dist_settings.lead_delivery_mode if dist_settings else LeadDeliveryMode.pull_broadcast

    # Deliver queued (not yet seen) leads from the pool, respecting distribution mode
    dispatched = await deliver_queued_leads_to_user(user, db, redis, mode=mode, notify_delay=2.0)

    await db.commit()
    logger.info("Icebreaker: tg_id=%s dispatched=%s", body.telegram_id, dispatched)
    return IcebreakerOut(dispatched=dispatched)


@router.post(
    "/icebreaker/stop",
    summary="Остановить ледокол — деактивировать получение лидов",
)
async def bot_stop_icebreaker(
    body: StopIcebreakerIn,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_result = await db.execute(
        select(User).where(User.telegram_id == body.telegram_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    user.icebreaker_active = False
    await db.commit()
    logger.info("Icebreaker stopped: tg_id=%s", body.telegram_id)
    return {"ok": True}


# ── Mini App endpoints ──────────────────────────────────────────────────────


@miniapp_router.get(
    "/user",
    response_model=MiniAppUserOut,
    summary="Получить данные пользователя для Mini App",
)
async def miniapp_get_user(
    x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> MiniAppUserOut:
    tg_user = _validate_init_data(x_telegram_init_data)
    tg_id = tg_user.get("id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing user id")

    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-register on first Mini App open
        user = User(
            telegram_id=tg_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await enqueue_user(tg_id, redis)

    return MiniAppUserOut(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        limit_count=user.limit_count,
    )


@miniapp_router.post(
    "/buy",
    response_model=MiniAppBuyOut,
    summary="Покупка лимитов",
)
async def miniapp_buy(
    body: MiniAppBuyIn,
    x_telegram_init_data: str = Header(default="", alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> MiniAppBuyOut:
    tg_user = _validate_init_data(x_telegram_init_data)
    tg_id = tg_user.get("id")
    if not tg_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing user id")

    if body.package_id not in PACKAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown package_id: {body.package_id!r}. Valid: {list(PACKAGES)}",
        )

    provider = get_provider()
    invoice = await provider.create_invoice(
        tg_id=tg_id,
        amount=body.amount,
        package_id=body.package_id,
    )

    # Stub provider: no redirect needed, credit immediately
    if invoice.invoice_url is None:
        new_limit = await credit_limits(
            tg_id=tg_id,
            amount=invoice.amount,
            payment_id=invoice.payment_id,
            db=db,
        )
        logger.info(
            "Stub purchase: tg_id=%s package=%s amount=%s new_limit=%s payment_id=%s",
            tg_id, body.package_id, invoice.amount, new_limit, invoice.payment_id,
        )
        return MiniAppBuyOut(
            status="created",
            payment_id=invoice.payment_id,
            invoice_url=None,
            message=f"Успешно! Начислено {invoice.amount} лимитов. Баланс: {new_limit}.",
        )

    # Real provider: redirect user to payment page
    return MiniAppBuyOut(
        status="created",
        payment_id=invoice.payment_id,
        invoice_url=invoice.invoice_url,
        message="Перейдите по ссылке для оплаты.",
    )
