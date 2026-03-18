from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionType
from app.models.user import User


async def credit_limits(
    tg_id: int,
    amount: int,
    payment_id: str,
    db: AsyncSession,
) -> int:
    """
    Atomically credit `amount` limits to the user identified by `tg_id`.
    Creates a Transaction record of type `purchase` with `payment_id` as the source.
    Returns the new limit_count.
    Raises HTTP 404 if the user does not exist.
    """
    async with db.begin():
        result = await db.execute(
            select(User).where(User.telegram_id == tg_id).with_for_update()
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user_not_found",
            )

        user.limit_count += amount

        db.add(
            Transaction(
                user_id=user.id,
                type=TransactionType.purchase,
                amount=amount,
                comment=f"Покупка через платёжный провайдер",
                source=payment_id,
            )
        )

    return user.limit_count
