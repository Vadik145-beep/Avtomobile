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


def _extract_country(structured: dict, agreements: str | None, transcript: str | None = None) -> str | None:
    explicit = structured.get("country") or structured.get("Страна")
    if explicit:
        return explicit
    for text in [agreements, transcript]:
        if not text:
            continue
        t = text.lower()
        if "корея" in t or "korean" in t or "корей" in t or "кореи" in t:
            return "Корея"
        if "китай" in t or "china" in t or "китайск" in t:
            return "Китай"
    return None


def _parse_transcript(transcript: str | None) -> dict:
    """Extract name, city, timing from call transcript when structured_data is missing."""
    if not transcript:
        return {}

    result: dict = {}
    lines = [ln.strip() for ln in transcript.split("\n") if ln.strip()]

    for i, line in enumerate(lines):
        if not line.startswith("AI:"):
            continue

        ai_lower = line.lower()

        # Next user response (look at most 3 lines ahead)
        next_user: str | None = None
        next_user_idx: int = -1
        for j in range(i + 1, min(i + 4, len(lines))):
            if lines[j].startswith("User:"):
                raw = lines[j][5:].strip().rstrip(".,!? ")
                if raw:
                    next_user = raw
                    next_user_idx = j
                break
            if lines[j].startswith("AI:"):
                break

        if not next_user or len(next_user) > 150:
            continue

        # Name — AI asks how to address the caller
        if ("обращаться" in ai_lower or "как к вам" in ai_lower or "как вас зовут" in ai_lower) \
                and "name" not in result:
            result["name"] = next_user

        # City — overwrite each time so the last (corrected) answer wins.
        # Prefer to extract the confirmed city from the AI's next line (e.g. "Отлично, Иркутск,...")
        elif "каком городе" in ai_lower or "каком российском городе" in ai_lower:
            city_value = next_user
            # Look for AI confirmation in the next few lines after user's reply
            if next_user_idx >= 0:
                for k in range(next_user_idx + 1, min(next_user_idx + 3, len(lines))):
                    if lines[k].startswith("AI:"):
                        ai_confirm = lines[k][3:].strip()
                        # AI often starts with "Отлично, <City>," or "Понял, <City>."
                        import re
                        m = re.match(
                            r"(?:отлично|понял|принято|хорошо)[,.]?\s+([А-ЯЁа-яё][а-яё]+)",
                            ai_confirm,
                            re.IGNORECASE,
                        )
                        if m:
                            city_value = m.group(1)
                        break
            result["city"] = city_value

        # Country — AI asks Korea or China
        elif ("кореи или китая" in ai_lower or "корея или китай" in ai_lower
              or ("корея" in ai_lower and "китай" in ai_lower)):
            lower_resp = next_user.lower()
            if any(w in lower_resp for w in ("корея", "корей", "кореи", "korean")):
                result["country"] = "Корея"
            elif any(w in lower_resp for w in ("китай", "китайск", "china")):
                result["country"] = "Китай"

        # Timing — AI asks when the car is needed
        elif "timing" not in result and "когда" in ai_lower and any(
            w in ai_lower for w in ("машин", "автомобил", "авто", "получить", "сроки", "срок")
        ):
            result["timing"] = next_user

    return result


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
    logger.info("Lidozvon RAW call_id=%s phone=%r structured=%r", payload.call_id, payload.phone, structured)

    agreements = structured.get("agreements") or structured.get("Договорённости") or None
    about_client = structured.get("about_client") or structured.get("О клиенте") or None

    # Structured_data may only contain `agreements` — fall back to transcript parsing
    parsed = _parse_transcript(payload.transcript)
    logger.info("Lidozvon transcript_parsed call_id=%s: %s", payload.call_id, parsed)

    client_name = (
        structured.get("name") or structured.get("Имя") or structured.get("Имя клиента")
        or parsed.get("name") or None
    )
    city = structured.get("city") or structured.get("Город") or parsed.get("city") or None
    timing = (
        structured.get("timing") or structured.get("Сроки") or structured.get("Срок")
        or parsed.get("timing") or None
    )
    country_origin = _extract_country(structured, agreements, payload.transcript)
    if not country_origin and parsed.get("country"):
        country_origin = parsed["country"]

    lead = Lead(
        call_id=payload.call_id,
        client_name=client_name,
        country_origin=country_origin,
        timing=timing,
        city=city,
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
