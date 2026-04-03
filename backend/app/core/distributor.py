import logging
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distribution_setting import DistributionSetting, LeadDeliveryMode
from app.models.lead import Lead
from app.models.lead_delivery import DeliveryStatus, LeadDelivery
from app.models.transaction import Transaction, TransactionType
from app.models.user import User

logger = logging.getLogger(__name__)

REDIS_QUEUE_KEY = "queue:users"
LEAD_NOTIFY_STREAM = "leads:notify"


async def distribute_lead(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Distribute a new lead to users according to current settings.

    In pull mode (pull_broadcast / pull_exclusive) leads are delivered
    only to users who have already activated the icebreaker and have
    enough balance.  No delivery is created for idle users — they will
    receive queued leads when they press the icebreaker button.
    """
    settings = await _get_current_settings(db)

    if settings.lead_delivery_mode == LeadDeliveryMode.pull_broadcast:
        return await _dispatch_broadcast(lead, db, redis)
    else:
        return await _dispatch_exclusive(lead, db, redis)


async def _dispatch_broadcast(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Send lead to ALL users who have icebreaker_active=True and balance > 0.
    Each user spends 1 limit.
    """
    users_result = await db.execute(
        select(User).where(
            User.is_active == True,           # noqa: E712
            User.icebreaker_active == True,   # noqa: E712
            User.limit_count >= 1,
        )
    )
    users = users_result.scalars().all()

    if not users:
        logger.info("pull_broadcast: no icebreaker-active users for lead %s", lead.id)
        return 0

    count = 0
    for user in users:
        already = await db.execute(
            select(LeadDelivery).where(
                LeadDelivery.lead_id == lead.id,
                LeadDelivery.user_id == user.id,
            )
        )
        if already.scalar_one_or_none() is not None:
            continue

        user.limit_count -= 1
        await _create_delivery_and_notify(user, lead, db, redis, source="icebreaker_broadcast")
        count += 1

    return count


async def _dispatch_exclusive(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Send lead to the FIRST icebreaker-active user with balance > 0 (FIFO by activation time).
    """
    user_result = await db.execute(
        select(User).where(
            User.is_active == True,          # noqa: E712
            User.icebreaker_active == True,  # noqa: E712
            User.limit_count >= 1,
        ).order_by(User.created_at.asc()).limit(1)
    )
    user = user_result.scalar_one_or_none()

    if user is None:
        logger.info("pull_exclusive: no eligible icebreaker-active user for lead %s", lead.id)
        return 0

    user.limit_count -= 1
    await _create_delivery_and_notify(user, lead, db, redis, source="icebreaker_exclusive")
    return 1


async def dispatch_lead_to_icebreaker_users(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Called after a new lead is saved (admin / webhook).
    Immediately delivers to currently active icebreaker users.
    """
    return await distribute_lead(lead, db, redis)


async def deliver_queued_leads_to_user(user: User, db: AsyncSession, redis: Redis) -> int:
    """
    Deliver all pending (not yet delivered) leads from the DB pool to a single user.
    Called when the user activates the icebreaker.
    Returns the number of leads dispatched.
    """
    if user.limit_count <= 0:
        return 0

    already_subq = (
        select(LeadDelivery.lead_id)
        .where(LeadDelivery.user_id == user.id)
        .scalar_subquery()
    )

    limit = min(user.limit_count, 50)
    leads_result = await db.execute(
        select(Lead)
        .where(Lead.is_test == False, Lead.id.not_in(already_subq))  # noqa: E712
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    leads = leads_result.scalars().all()

    dispatched = 0
    for lead in leads:
        if user.limit_count <= 0:
            break
        user.limit_count -= 1
        await _create_delivery_and_notify(user, lead, db, redis, source="icebreaker_queue")
        dispatched += 1

    return dispatched


async def _create_delivery_and_notify(
    user: User, lead: Lead, db: AsyncSession, redis: Redis, source: str
) -> None:
    delivery = LeadDelivery(
        lead_id=lead.id,
        user_id=user.id,
        status=DeliveryStatus.opened,
        opened_at=datetime.now(timezone.utc),
    )
    db.add(delivery)
    db.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.debit,
            amount=1,
            comment=f"Ледокол: лид #{lead.id}",
            source=source,
        )
    )
    await db.flush()

    await redis.xadd(
        LEAD_NOTIFY_STREAM,
        {
            "lead_id": str(lead.id),
            "user_tg_id": str(user.telegram_id),
            "delivery_id": str(delivery.id),
            "client_name": lead.client_name or "",
            "country_origin": lead.country_origin or "",
            "timing": lead.timing or "",
            "city": lead.city or "",
            "phone": lead.phone_encrypted or "",
        },
    )
    logger.debug("Lead %s dispatched to user tg_id=%s via %s", lead.id, user.telegram_id, source)


async def _get_current_settings(db: AsyncSession) -> DistributionSetting:
    result = await db.execute(select(DistributionSetting).limit(1))
    settings = result.scalar_one_or_none()
    if settings is None:
        return DistributionSetting(
            lead_delivery_mode=LeadDeliveryMode.pull_broadcast,
        )
    return settings


async def enqueue_user(tg_id: int, redis: Redis) -> None:
    """Add a user to the exclusive distribution queue (LPUSH so RPOP gives FIFO)."""
    await redis.lpush(REDIS_QUEUE_KEY, str(tg_id))


async def remove_user_from_queue(tg_id: int, redis: Redis) -> None:
    """Remove all occurrences of a user from the exclusive queue."""
    await redis.lrem(REDIS_QUEUE_KEY, 0, str(tg_id))
