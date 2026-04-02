import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.credit import credit_limits
from app.core.distributor import distribute_lead
from app.core.security import verify_lidozvon_token
from app.database import get_db
from app.dependencies import get_redis
from app.models.distribution_setting import DistributionSetting
from app.models.lead import DistributionMode, Lead
from app.payments.factory import get_provider
from app.schemas.lead import LidozvonWebhookIn, LeadOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post(
    "/lidozvon",
    dependencies=[Depends(verify_lidozvon_token)],
    summary="Принять лид от Лидозвон",
)
async def receive_lidozvon(
    payload: LidozvonWebhookIn,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> dict[str, Any]:
    if payload.is_qualified is False and not payload.test:
        logger.info(
            "Lead call_id=%s not qualified (%s) — skipped",
            payload.call_id,
            payload.qualification_reason,
        )
        return {"status": "not_qualified"}

    existing = await db.execute(
        select(Lead).where(Lead.call_id == payload.call_id)
    )
    if existing.scalar_one_or_none() is not None:
        logger.info("Duplicate lead call_id=%s — skipped", payload.call_id)
        return {"status": "duplicate"}

    settings_result = await db.execute(select(DistributionSetting).limit(1))
    settings = settings_result.scalar_one_or_none()
    current_mode: DistributionMode = (
        settings.mode if settings else DistributionMode.coverage
    )

    structured = payload.structured_data or {}
    lead = Lead(
        call_id=payload.call_id,
        client_name=structured.get("name") or None,
        country_origin=structured.get("country") or None,
        timing=structured.get("timing") or None,
        city=structured.get("city") or None,
        summary=payload.transcript,
        transcript=payload.transcript,
        phone_encrypted=payload.phone,
        recording_url=payload.recording_url or "",
        is_qualified=payload.is_qualified,
        is_test=bool(payload.test),
        distribution_mode=current_mode,
    )
    db.add(lead)
    await db.flush()

    if payload.test:
        await db.commit()
        logger.info("Lidozvon test webhook call_id=%s — saved without distribution", payload.call_id)
        return {"status": "test_saved", "id": lead.id}

    notified = await distribute_lead(lead, db, redis)
    await db.commit()

    logger.info("Lead #%s (call_id=%s) received, notified %s users", lead.id, payload.call_id, notified)
    return LeadOut.model_validate(lead).model_dump()


@router.post(
    "/payment",
    summary="Вебхук подтверждения платежа от провайдера",
)
async def receive_payment(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    body = await request.json()
    logger.info("Payment webhook payload: %s", body)

    provider = get_provider()
    try:
        result = await provider.verify_webhook(body)
    except ValueError as exc:
        logger.warning("Payment webhook rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not result.verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_not_verified",
        )

    new_limit = await credit_limits(
        tg_id=result.tg_id,
        amount=result.amount,
        payment_id=result.payment_id,
        db=db,
    )
    logger.info(
        "Payment confirmed: tg_id=%s amount=%s payment_id=%s new_limit=%s",
        result.tg_id, result.amount, result.payment_id, new_limit,
    )
    return {"ok": True, "credited": result.amount, "new_limit": new_limit}
