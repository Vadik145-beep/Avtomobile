from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.distributor import (
    deliver_queued_leads_to_user,
    dispatch_lead_to_icebreaker_users,
    enqueue_user,
    remove_user_from_queue,
    reset_exclusive_queue,
)
from app.core.security import create_access_token, get_current_admin, verify_password
from app.database import get_db
from app.dependencies import get_redis
from app.models.distribution_setting import DistributionSetting, LeadDeliveryMode
from app.models.lead import Lead, ModerationStatus
from app.models.lead_delivery import LeadDelivery
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.admin import (
    BonusIn,
    DeductIn,
    DeliveryInfo,
    IcebreakerToggleIn,
    LeadAdminOut,
    LeadCreateIn,
    LoginIn,
    SettingsIn,
    SettingsOut,
    StatsOut,
    TokenOut,
)
from app.schemas.transaction import TransactionOut
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=TokenOut, summary="Авторизация администратора")
async def admin_login(body: LoginIn) -> TokenOut:
    if body.username != settings.admin_username or not verify_password(
        body.password, settings.admin_password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(
        {"sub": body.username},
        expires_delta=timedelta(hours=settings.admin_jwt_expire_hours),
    )
    return TokenOut(access_token=token)


@router.get(
    "/stats",
    response_model=StatsOut,
    dependencies=[Depends(get_current_admin)],
    summary="Сводная статистика",
)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsOut:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    users_total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    leads_today = (
        await db.execute(
            select(func.count()).select_from(Lead).where(
                Lead.created_at >= today_start,
                Lead.moderation_status == ModerationStatus.approved,
            )
        )
    ).scalar_one()
    leads_week = (
        await db.execute(
            select(func.count()).select_from(Lead).where(
                Lead.created_at >= week_start,
                Lead.moderation_status == ModerationStatus.approved,
            )
        )
    ).scalar_one()
    leads_month = (
        await db.execute(
            select(func.count()).select_from(Lead).where(
                Lead.created_at >= month_start,
                Lead.moderation_status == ModerationStatus.approved,
            )
        )
    ).scalar_one()

    return StatsOut(
        users_total=users_total,
        leads_today=leads_today,
        leads_week=leads_week,
        leads_month=leads_month,
    )


@router.get(
    "/settings",
    response_model=SettingsOut,
    dependencies=[Depends(get_current_admin)],
    summary="Текущий режим дистрибуции",
)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsOut:
    result = await db.execute(select(DistributionSetting).limit(1))
    s = result.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Settings not found")
    return SettingsOut.model_validate(s)


@router.put(
    "/settings",
    response_model=SettingsOut,
    dependencies=[Depends(get_current_admin)],
    summary="Изменить режим дистрибуции",
)
async def update_settings(
    body: SettingsIn,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> SettingsOut:
    result = await db.execute(select(DistributionSetting).limit(1))
    s = result.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Settings not found")

    s.lead_delivery_mode = body.lead_delivery_mode
    s.updated_by = None
    await db.commit()
    await db.refresh(s)
    return SettingsOut.model_validate(s)


@router.post(
    "/queue/reset",
    dependencies=[Depends(get_current_admin)],
    summary="Пересбросить очередь exclusive-режима",
)
async def reset_queue(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    count = await reset_exclusive_queue(db, redis)
    return {"queued": count}


@router.get(
    "/users",
    response_model=list[UserOut],
    dependencies=[Depends(get_current_admin)],
    summary="Список пользователей",
)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    return [UserOut.model_validate(u) for u in result.scalars().all()]


@router.get(
    "/users/{tg_id}",
    response_model=UserOut,
    dependencies=[Depends(get_current_admin)],
    summary="Пользователь по telegram_id",
)
async def get_user(tg_id: int, db: AsyncSession = Depends(get_db)) -> UserOut:
    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)


@router.post(
    "/users/{tg_id}/bonus",
    response_model=UserOut,
    dependencies=[Depends(get_current_admin)],
    summary="Начислить бонус пользователю",
)
async def add_bonus(
    tg_id: int,
    body: BonusIn,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> UserOut:
    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.limit_count += body.amount
    db.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.bonus,
            amount=body.amount,
            comment=body.comment,
            source="admin",
        )
    )
    await db.commit()
    await db.refresh(user)

    # If icebreaker is active and balance just became positive — re-enqueue
    if user.icebreaker_active and user.limit_count > 0:
        await enqueue_user(user.telegram_id, redis)

    return UserOut.model_validate(user)


@router.post(
    "/users/{tg_id}/deduct",
    response_model=UserOut,
    dependencies=[Depends(get_current_admin)],
    summary="Снять лимиты у пользователя",
)
async def deduct_balance(
    tg_id: int,
    body: DeductIn,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> UserOut:
    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.limit_count < body.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно лимитов: доступно {user.limit_count}, запрошено {body.amount}",
        )
    user.limit_count -= body.amount
    if user.limit_count <= 0:
        user.icebreaker_active = False
    db.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.debit,
            amount=body.amount,
            comment=body.comment,
            source="admin",
        )
    )
    await db.commit()
    if user.limit_count <= 0:
        await remove_user_from_queue(user.telegram_id, redis)
        await redis.xadd(BOT_KEYBOARD_UPDATE_STREAM, {
            "telegram_id": str(user.telegram_id),
            "icebreaker_active": "0",
            "reason": "balance_empty",
        })
    await db.refresh(user)
    return UserOut.model_validate(user)


BOT_KEYBOARD_UPDATE_STREAM = "bot:keyboard_update"


@router.post(
    "/users/{tg_id}/icebreaker",
    response_model=UserOut,
    dependencies=[Depends(get_current_admin)],
    summary="Включить / выключить ледокол для пользователя",
)
async def toggle_icebreaker(
    tg_id: int,
    body: IcebreakerToggleIn,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> UserOut:
    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.icebreaker_active = body.active
    await db.commit()
    await db.refresh(user)

    if body.active:
        await enqueue_user(tg_id, redis)
        settings_result = await db.execute(select(DistributionSetting).limit(1))
        dist_settings = settings_result.scalar_one_or_none()
        mode = dist_settings.lead_delivery_mode if dist_settings else LeadDeliveryMode.pull_broadcast
        await deliver_queued_leads_to_user(user, db, redis, mode=mode, notify_delay=3.0)
        await db.commit()
    else:
        await remove_user_from_queue(tg_id, redis)

    await redis.xadd(
        BOT_KEYBOARD_UPDATE_STREAM,
        {"telegram_id": str(tg_id), "icebreaker_active": "1" if body.active else "0"},
    )

    return UserOut.model_validate(user)


@router.get(
    "/users/{tg_id}/transactions",
    response_model=list[TransactionOut],
    dependencies=[Depends(get_current_admin)],
    summary="История транзакций пользователя",
)
async def user_transactions(
    tg_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[TransactionOut]:
    user_result = await db.execute(select(User).where(User.telegram_id == tg_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [TransactionOut.model_validate(t) for t in result.scalars().all()]


@router.get(
    "/leads",
    response_model=list[LeadAdminOut],
    dependencies=[Depends(get_current_admin)],
    summary="Список лидов с информацией о доставке",
)
async def list_leads(
    skip: int = 0,
    limit: int = 50,
    moderation_status: ModerationStatus | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[LeadAdminOut]:
    query = (
        select(Lead)
        .options(
            selectinload(Lead.deliveries).selectinload(LeadDelivery.user)
        )
        .order_by(Lead.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if moderation_status is not None:
        query = query.where(Lead.moderation_status == moderation_status)

    result = await db.execute(query)
    leads = result.scalars().all()

    out = []
    for lead in leads:
        deliveries = [
            DeliveryInfo(
                status=d.status.value,
                username=d.user.username,
                first_name=d.user.first_name,
                telegram_id=d.user.telegram_id,
                opened_at=d.opened_at,
            )
            for d in lead.deliveries
        ]
        out.append(
            LeadAdminOut(
                id=lead.id,
                call_id=lead.call_id,
                client_name=lead.client_name,
                country_origin=lead.country_origin,
                timing=lead.timing,
                city=lead.city,
                phone=lead.phone_encrypted,
                agreements=lead.agreements,
                about_client=lead.about_client,
                created_at=lead.created_at,
                is_test=lead.is_test,
                moderation_status=lead.moderation_status,
                deliveries=deliveries,
            )
        )
    return out


@router.post(
    "/leads/{lead_id}/approve",
    response_model=LeadAdminOut,
    dependencies=[Depends(get_current_admin)],
    summary="Одобрить лид и запустить рассылку",
)
async def approve_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> LeadAdminOut:
    result = await db.execute(
        select(Lead)
        .options(selectinload(Lead.deliveries).selectinload(LeadDelivery.user))
        .where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.moderation_status != ModerationStatus.pending:
        raise HTTPException(status_code=400, detail="Lead is not pending moderation")

    lead.moderation_status = ModerationStatus.approved
    await db.flush()

    if not lead.is_test:
        await dispatch_lead_to_icebreaker_users(lead, db, redis)

    await db.commit()
    await db.refresh(lead)

    deliveries = [
        DeliveryInfo(
            status=d.status.value,
            username=d.user.username,
            first_name=d.user.first_name,
            telegram_id=d.user.telegram_id,
            opened_at=d.opened_at,
        )
        for d in lead.deliveries
    ]
    return LeadAdminOut(
        id=lead.id,
        call_id=lead.call_id,
        client_name=lead.client_name,
        country_origin=lead.country_origin,
        timing=lead.timing,
        city=lead.city,
        phone=lead.phone_encrypted,
        agreements=lead.agreements,
        about_client=lead.about_client,
        created_at=lead.created_at,
        is_test=lead.is_test,
        moderation_status=lead.moderation_status,
        deliveries=deliveries,
    )


@router.post(
    "/leads/{lead_id}/reject",
    response_model=LeadAdminOut,
    dependencies=[Depends(get_current_admin)],
    summary="Отклонить лид",
)
async def reject_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
) -> LeadAdminOut:
    result = await db.execute(
        select(Lead)
        .options(selectinload(Lead.deliveries).selectinload(LeadDelivery.user))
        .where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.moderation_status != ModerationStatus.pending:
        raise HTTPException(status_code=400, detail="Lead is not pending moderation")

    lead.moderation_status = ModerationStatus.rejected
    await db.commit()
    await db.refresh(lead)

    return LeadAdminOut(
        id=lead.id,
        call_id=lead.call_id,
        client_name=lead.client_name,
        country_origin=lead.country_origin,
        timing=lead.timing,
        city=lead.city,
        phone=lead.phone_encrypted,
        agreements=lead.agreements,
        about_client=lead.about_client,
        created_at=lead.created_at,
        is_test=lead.is_test,
        moderation_status=lead.moderation_status,
        deliveries=[],
    )


@router.post(
    "/leads",
    response_model=LeadAdminOut,
    dependencies=[Depends(get_current_admin)],
    summary="Создать лид вручную",
)
async def create_lead(
    body: LeadCreateIn,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> LeadAdminOut:
    moderation_status = ModerationStatus.pending if body.pending_moderation else ModerationStatus.approved
    lead = Lead(
        call_id=None,
        client_name=body.client_name,
        country_origin=body.country_origin,
        timing=body.timing,
        city=body.city,
        summary=body.summary,
        agreements=body.agreements,
        about_client=body.about_client,
        transcript=None,
        phone_encrypted=body.phone,
        recording_url="",
        is_qualified=True,
        is_test=body.is_test,
        moderation_status=moderation_status,
    )
    db.add(lead)
    await db.flush()
    if not body.is_test and not body.pending_moderation:
        await dispatch_lead_to_icebreaker_users(lead, db, redis)
    await db.commit()
    await db.refresh(lead)
    return LeadAdminOut(
        id=lead.id,
        call_id=lead.call_id,
        client_name=lead.client_name,
        country_origin=lead.country_origin,
        timing=lead.timing,
        city=lead.city,
        phone=lead.phone_encrypted,
        agreements=lead.agreements,
        about_client=lead.about_client,
        created_at=lead.created_at,
        is_test=lead.is_test,
        moderation_status=lead.moderation_status,
        deliveries=[],
    )


@router.delete(
    "/leads/{lead_id}",
    dependencies=[Depends(get_current_admin)],
    summary="Удалить лид",
)
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.execute(delete(LeadDelivery).where(LeadDelivery.lead_id == lead_id))
    await db.delete(lead)
    await db.commit()
    return {"ok": True, "deleted_id": lead_id}
