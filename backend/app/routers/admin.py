from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.distributor import distribute_lead
from app.core.security import create_access_token, get_current_admin, verify_password
from app.database import get_db
from app.dependencies import get_redis
from app.models.distribution_setting import DistributionSetting
from app.models.lead import Lead
from app.models.lead_delivery import LeadDelivery
from app.models.transaction import Transaction, TransactionType
from app.models.user import User
from app.schemas.admin import (
    BonusIn,
    DeliveryInfo,
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
            select(func.count()).select_from(Lead).where(Lead.created_at >= today_start)
        )
    ).scalar_one()
    leads_week = (
        await db.execute(
            select(func.count()).select_from(Lead).where(Lead.created_at >= week_start)
        )
    ).scalar_one()
    leads_month = (
        await db.execute(
            select(func.count()).select_from(Lead).where(Lead.created_at >= month_start)
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

    s.mode = body.mode
    s.speed_group_size = body.speed_group_size
    s.updated_by = None  # admin username, not tg_id; field is BigInteger so keep None
    await db.commit()
    await db.refresh(s)
    return SettingsOut.model_validate(s)


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
    db: AsyncSession = Depends(get_db),
) -> list[LeadAdminOut]:
    result = await db.execute(
        select(Lead)
        .options(
            selectinload(Lead.deliveries).selectinload(LeadDelivery.user)
        )
        .order_by(Lead.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
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
                brand=lead.brand,
                city=lead.city,
                phone=lead.phone_encrypted,
                created_at=lead.created_at,
                distribution_mode=lead.distribution_mode.value,
                is_test=lead.is_test,
                deliveries=deliveries,
            )
        )
    return out


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
    lead = Lead(
        call_id=None,
        brand=body.brand,
        city=body.city,
        summary=body.summary,
        transcript=None,
        phone_encrypted=body.phone,
        recording_url="",
        is_qualified=True,
        is_test=body.is_test,
        distribution_mode=body.distribution_mode,
    )
    db.add(lead)
    await db.flush()
    if not body.is_test:
        await distribute_lead(lead, db, redis)
    await db.commit()
    await db.refresh(lead)
    return LeadAdminOut(
        id=lead.id,
        call_id=lead.call_id,
        brand=lead.brand,
        city=lead.city,
        phone=lead.phone_encrypted,
        created_at=lead.created_at,
        distribution_mode=lead.distribution_mode.value,
        is_test=lead.is_test,
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

    await db.delete(lead)
    await db.commit()
    return {"ok": True, "deleted_id": lead_id}
