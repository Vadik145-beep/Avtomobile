import logging

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distribution_setting import DistributionSetting
from app.models.lead import DistributionMode, Lead
from app.models.lead_delivery import DeliveryStatus, LeadDelivery
from app.models.user import User

logger = logging.getLogger(__name__)

REDIS_QUEUE_KEY = "queue:users"
LEAD_NOTIFY_STREAM = "leads:notify"


async def distribute_lead(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Distribute a lead to users according to current distribution settings.
    Returns the number of users notified.
    """
    settings = await _get_current_settings(db)
    mode = settings.mode

    if mode == DistributionMode.exclusive:
        return await _distribute_exclusive(lead, db, redis)
    elif mode == DistributionMode.speed:
        return await _distribute_speed(lead, db, redis, settings.speed_group_size)
    else:
        return await _distribute_coverage(lead, db, redis)


async def _distribute_exclusive(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Pop one user from the Redis queue and send the lead only to that user.
    """
    raw = await redis.rpop(REDIS_QUEUE_KEY)
    if raw is None:
        logger.warning("Exclusive mode: queue is empty, lead %s not delivered", lead.id)
        return 0

    tg_id = int(raw)
    user_result = await db.execute(
        select(User).where(User.telegram_id == tg_id, User.is_active == True)  # noqa: E712
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        logger.warning("Exclusive mode: user tg_id=%s not found or inactive", tg_id)
        return 0

    await _send_lead_to_user(user, lead, db, redis)
    return 1


async def _distribute_speed(lead: Lead, db: AsyncSession, redis: Redis, group_size: int) -> int:
    """
    Send the lead to the first N active users; use SETNX to ensure only the
    first user who opens the contact wins (race-condition guard in debit.py).
    """
    users_result = await db.execute(
        select(User)
        .where(User.is_active == True, User.limit_count >= 1)  # noqa: E712
        .limit(group_size)
    )
    users = users_result.scalars().all()

    if not users:
        logger.warning("Speed mode: no eligible users for lead %s", lead.id)
        return 0

    # Mark the lead as claimable — first opener wins, rest get delivery blocked
    lock_key = f"lead:{lead.id}:claimed"
    await redis.set(lock_key, "", nx=True, ex=3600)

    for user in users:
        await _send_lead_to_user(user, lead, db, redis)

    return len(users)


async def _distribute_coverage(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Broadcast the lead to all active users who have at least 1 limit.
    """
    users_result = await db.execute(
        select(User).where(User.is_active == True, User.limit_count >= 1)  # noqa: E712
    )
    users = users_result.scalars().all()

    if not users:
        logger.warning("Coverage mode: no eligible users for lead %s", lead.id)
        return 0

    for user in users:
        await _send_lead_to_user(user, lead, db, redis)

    return len(users)


async def _send_lead_to_user(user: User, lead: Lead, db: AsyncSession, redis: Redis) -> None:
    """
    Create a lead_delivery record and publish a notification event to Redis Stream.
    """
    delivery = LeadDelivery(
        lead_id=lead.id,
        user_id=user.id,
        status=DeliveryStatus.sent,
    )
    db.add(delivery)
    await db.flush()  # get delivery.id without committing

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
    logger.debug("Lead %s dispatched to user tg_id=%s", lead.id, user.telegram_id)


async def _get_current_settings(db: AsyncSession) -> DistributionSetting:
    result = await db.execute(select(DistributionSetting).limit(1))
    settings = result.scalar_one_or_none()
    if settings is None:
        # Fallback default — should not happen after initial migration
        return DistributionSetting(mode=DistributionMode.coverage, speed_group_size=5)
    return settings


async def enqueue_user(tg_id: int, redis: Redis) -> None:
    """Add a user to the exclusive distribution queue (LPUSH so RPOP gives FIFO)."""
    await redis.lpush(REDIS_QUEUE_KEY, str(tg_id))


async def remove_user_from_queue(tg_id: int, redis: Redis) -> None:
    """Remove all occurrences of a user from the exclusive queue."""
    await redis.lrem(REDIS_QUEUE_KEY, 0, str(tg_id))
