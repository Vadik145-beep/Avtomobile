import logging
from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distribution_setting import DistributionSetting, LeadDeliveryMode
from app.models.lead import Lead, ModerationStatus
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
        if user.limit_count <= 0:
            user.icebreaker_active = False
        await _create_delivery_and_notify(user, lead, db, redis, source="icebreaker_broadcast")
        count += 1

    return count


async def _dispatch_exclusive(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Send lead to the FIRST icebreaker-active user with balance > 0.
    User order is determined by the Redis FIFO queue (queue:users).
    After delivery the user is rotated to the back of the queue.
    """
    # Walk the Redis queue from the tail (head of FIFO) to find an eligible user
    queue_len = await redis.llen(REDIS_QUEUE_KEY)
    if queue_len == 0:
        logger.info("pull_exclusive: Redis queue is empty for lead %s", lead.id)
        return 0

    for position in range(queue_len - 1, -1, -1):
        tg_id_str = await redis.lindex(REDIS_QUEUE_KEY, position)
        if tg_id_str is None:
            continue

        user_result = await db.execute(
            select(User).where(
                User.telegram_id == int(tg_id_str),
                User.is_active == True,          # noqa: E712
                User.icebreaker_active == True,  # noqa: E712
                User.limit_count >= 1,
            )
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            continue

        # Rotate: remove this specific user from their current position and push to head
        await redis.lrem(REDIS_QUEUE_KEY, 1, tg_id_str)
        await redis.lpush(REDIS_QUEUE_KEY, tg_id_str)

        user.limit_count -= 1
        await _create_delivery_and_notify(user, lead, db, redis, source="icebreaker_exclusive")
        logger.info("pull_exclusive: lead %s dispatched to tg_id=%s", lead.id, tg_id_str)
        return 1

    logger.info("pull_exclusive: no eligible icebreaker-active user in queue for lead %s", lead.id)
    return 0


async def dispatch_lead_to_icebreaker_users(lead: Lead, db: AsyncSession, redis: Redis) -> int:
    """
    Called after a new lead is saved (admin / webhook).
    Immediately delivers to currently active icebreaker users.
    """
    return await distribute_lead(lead, db, redis)


async def deliver_queued_leads_to_user(
    user: User,
    db: AsyncSession,
    redis: Redis,
    mode: LeadDeliveryMode = LeadDeliveryMode.pull_broadcast,
) -> int:
    """
    Deliver pending (not yet delivered) leads from the DB pool to a single user.
    Called when the user activates the icebreaker.

    In pull_exclusive mode the user must be the current head of the Redis queue;
    otherwise 0 is returned — leads will arrive when it's their turn via distribute_lead.
    """
    if user.limit_count <= 0:
        return 0

    if mode == LeadDeliveryMode.pull_exclusive:
        head_tg_id = await redis.lindex(REDIS_QUEUE_KEY, -1)
        if head_tg_id is None or int(head_tg_id) != user.telegram_id:
            logger.info(
                "deliver_queued: tg_id=%s is not head of exclusive queue, skipping",
                user.telegram_id,
            )
            return 0

    already_subq = (
        select(LeadDelivery.lead_id)
        .where(LeadDelivery.user_id == user.id)
        .scalar_subquery()
    )

    limit = min(user.limit_count, 50)
    leads_result = await db.execute(
        select(Lead)
        .where(
            Lead.is_test == False,  # noqa: E712
            Lead.moderation_status == ModerationStatus.approved,
            Lead.id.not_in(already_subq),
        )
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


async def init_exclusive_queue(db: AsyncSession, redis: Redis) -> int:
    """
    Populate the Redis exclusive queue if it is empty.
    Users are added in created_at ASC order so the earliest registrant
    is served first (RPOP gives the tail = oldest = first in line).
    Returns the number of users added (0 if queue was already populated).
    """
    queue_len = await redis.llen(REDIS_QUEUE_KEY)
    if queue_len > 0:
        logger.info("Exclusive queue already has %d entries, skipping init", queue_len)
        return 0

    users_result = await db.execute(
        select(User)
        .where(User.is_active == True)  # noqa: E712
        .order_by(User.created_at.asc())
    )
    users = users_result.scalars().all()

    if not users:
        logger.info("Exclusive queue init: no active users found")
        return 0

    # lpush each user — last lpush'd ends up at tail (index -1) = first to be served
    for user in users:
        await redis.lpush(REDIS_QUEUE_KEY, str(user.telegram_id))

    logger.info("Exclusive queue initialized with %d users", len(users))
    return len(users)


async def reset_exclusive_queue(db: AsyncSession, redis: Redis) -> int:
    """
    Clear the Redis exclusive queue and rebuild it from the DB.
    Returns the number of users now in the queue.
    """
    await redis.delete(REDIS_QUEUE_KEY)
    logger.info("Exclusive queue cleared, rebuilding...")
    return await init_exclusive_queue(db, redis)


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
            "recording_url": lead.recording_url or "",
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
