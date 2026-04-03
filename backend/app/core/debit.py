from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lead import Lead
from app.models.lead_delivery import DeliveryStatus, LeadDelivery
from app.models.transaction import Transaction, TransactionType
from app.models.user import User


async def open_contact(tg_id: int, lead_id: int, db: AsyncSession) -> tuple[str, str]:
    """
    Atomically debit one limit from user and mark delivery as opened.
    Returns (phone, recording_url). Idempotent: repeated calls return data without debit.
    Raises HTTPException on limit_zero, delivery_not_found, already_taken (race).
    """
    async with db.begin():
        user_result = await db.execute(
            select(User).where(User.telegram_id == tg_id).with_for_update()
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user_not_found",
            )

        delivery_result = await db.execute(
            select(LeadDelivery)
            .where(LeadDelivery.lead_id == lead_id, LeadDelivery.user_id == user.id)
            .options(selectinload(LeadDelivery.lead))
            .with_for_update()
        )
        delivery = delivery_result.scalar_one_or_none()
        if delivery is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="delivery_not_found",
            )

        if delivery.status == DeliveryStatus.opened:
            # Idempotent — already opened before, no double debit
            lead = delivery.lead
            return _decrypt_phone(lead.phone_encrypted), lead.recording_url or ""

        if delivery.status == DeliveryStatus.blocked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="already_taken",
            )

        if user.limit_count < 1:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="limit_zero",
            )

        user.limit_count -= 1
        delivery.status = DeliveryStatus.opened
        delivery.opened_at = datetime.now(timezone.utc)

        db.add(
            Transaction(
                user_id=user.id,
                type=TransactionType.debit,
                amount=1,
                comment=f"Открытие контакта лида #{lead_id}",
                source="bot",
            )
        )

        lead = delivery.lead

    return _decrypt_phone(lead.phone_encrypted), lead.recording_url or ""


def _decrypt_phone(phone_encrypted: str | None) -> str:
    """
    Placeholder for decryption. Currently stores plain phone — extend with
    Fernet/AES-GCM when encryption is added to the webhook intake.
    """
    if phone_encrypted is None:
        return ""
    return phone_encrypted
