import asyncio
import logging

import redis.asyncio as aioredis
from aiogram import Bot

from app.config import settings

from app.templates import lead_card_text

logger = logging.getLogger(__name__)

STREAM_KEY = "leads:notify"
WORKER_LAST_ID_KEY = "bot:stream:last_id"


async def _send_lead_card(bot: Bot, data: dict) -> None:
    """Отправляет карточку лида пользователю."""
    try:
        user_tg_id = int(data[b"user_tg_id"])
        lead_id = int(data[b"lead_id"])
        delivery_id = int(data.get(b"delivery_id", b"0"))
        client_name = data.get(b"client_name", b"").decode()
        country_origin = data.get(b"country_origin", b"").decode()
        timing = data.get(b"timing", b"").decode()
        city = data.get(b"city", b"").decode()
        phone = data.get(b"phone", b"").decode()
    except (KeyError, ValueError):
        logger.warning("Некорректные поля сообщения из стрима: %s", data)
        return

    text = lead_card_text(
        client_name=client_name,
        phone=phone,
        country_origin=country_origin,
        city=city,
        timing=timing,
    )

    try:
        await bot.send_message(
            chat_id=user_tg_id,
            text=text,
            parse_mode="HTML",
        )
        logger.info(
            "Карточка лида отправлена: tg_id=%s lead_id=%s",
            user_tg_id,
            lead_id,
        )
    except Exception:
        logger.exception(
            "Ошибка отправки карточки лида tg_id=%s lead_id=%s", user_tg_id, lead_id
        )


async def stream_worker(bot: Bot) -> None:
    """Читает Redis Stream leads:notify и рассылает карточки лидов."""
    r = aioredis.from_url(settings.redis_url, decode_responses=False)

    # Resume from last processed position; if none — start from current tail ($ = only new messages)
    saved = await r.get(WORKER_LAST_ID_KEY)
    last_id = saved if saved else b"$"

    logger.info("Stream worker запущен, читаю %s с позиции %s", STREAM_KEY, last_id)

    while True:
        try:
            messages = await r.xread({STREAM_KEY: last_id}, block=5000, count=10)

            if not messages:
                continue

            for _stream, entries in messages:
                for msg_id, data in entries:
                    await _send_lead_card(bot, data)
                    last_id = msg_id
                    await r.set(WORKER_LAST_ID_KEY, last_id)

        except asyncio.CancelledError:
            logger.info("Stream worker остановлен.")
            break
        except Exception:
            logger.exception("Ошибка в stream worker, повтор через 5 сек.")
            await asyncio.sleep(5)

    await r.aclose()
