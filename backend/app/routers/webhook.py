import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.credit import credit_limits
from app.core.distributor import dispatch_lead_to_icebreaker_users, enqueue_user
from app.core.security import verify_lidozvon_token
from app.database import get_db
from app.dependencies import get_redis
from app.models.lead import Lead, ModerationStatus
from app.payments.factory import get_provider
from app.schemas.lead import LidozvonWebhookIn, LeadOut

logger = logging.getLogger(__name__)


def _extract_country(structured: dict, agreements: str | None) -> str | None:
    explicit = structured.get("country") or structured.get("Страна")
    if explicit:
        return explicit
    text = (agreements or "").lower()
    if "корея" in text or "korean" in text:
        return "Корея"
    if "китай" in text or "china" in text or "китайск" in text:
        return "Китай"
    return None


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

    existing_result = await db.execute(
        select(Lead).where(Lead.call_id == payload.call_id)
    )
    existing = existing_result.scalar_one_or_none()

    # Для тестовых лидов удаляем старую запись, чтобы каждый тест проходил заново
    if existing is not None:
        if payload.test:
            await db.delete(existing)
            await db.flush()
            logger.info("Test lead call_id=%s — old record deleted, re-saving", payload.call_id)
        else:
            logger.info("Duplicate lead call_id=%s — skipped", payload.call_id)
            return {"status": "duplicate"}

    structured = payload.structured_data or {}
    logger.debug("Lidozvon structured_data call_id=%s: %s", payload.call_id, structured)

    agreements = structured.get("agreements") or structured.get("Договорённости") or None
    about_client = structured.get("about_client") or structured.get("О клиенте") or None

    lead = Lead(
        call_id=payload.call_id,
        client_name=structured.get("name") or structured.get("Имя") or structured.get("Имя клиента") or None,
        country_origin=_extract_country(structured, agreements),
        timing=structured.get("timing") or structured.get("Сроки") or structured.get("Срок") or None,
        city=structured.get("city") or structured.get("Город") or None,
        summary=payload.transcript,
        transcript=payload.transcript,
        phone_encrypted=payload.phone,
        recording_url=payload.recording_url or "",
        is_qualified=payload.is_qualified,
        is_test=bool(payload.test),
        moderation_status=ModerationStatus.pending,
        agreements=agreements,
        about_client=about_client,
    )
    db.add(lead)
    await db.flush()

    if payload.test:
        await db.commit()
        logger.info("Lidozvon test webhook call_id=%s — saved, pending moderation", payload.call_id)
        return {"status": "test_saved", "id": lead.id}

    await db.commit()

    logger.info("Lead #%s (call_id=%s) received, pending moderation", lead.id, payload.call_id)
    return LeadOut.model_validate(lead).model_dump()


@router.post(
    "/payment",
    summary="Вебхук подтверждения платежа от провайдера",
)
async def receive_payment(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
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

    new_limit, icebreaker_active = await credit_limits(
        tg_id=result.tg_id,
        amount=result.amount,
        payment_id=result.payment_id,
        db=db,
    )
    logger.info(
        "Payment confirmed: tg_id=%s amount=%s payment_id=%s new_limit=%s",
        result.tg_id, result.amount, result.payment_id, new_limit,
    )

    # Re-enqueue if icebreaker was active and balance just became positive
    if icebreaker_active and new_limit > 0:
        await enqueue_user(result.tg_id, redis)

    return {"ok": True, "credited": result.amount, "new_limit": new_limit}
