import asyncio
import logging

import redis.asyncio as aioredis
from aiogram import Bot

from app.config import settings
from app.keyboards import lead_card_keyboard
from app.templates import lead_card_text

logger = logging.getLogger(__name__)

STREAM_KEY = "leads:notify"
WORKER_LAST_ID_KEY = "bot:stream:last_id"


async def _send_lead_card(bot: Bot, data: dict) -> None:
    """Отправляет карточку лида пользователю."""
    try:
        user_tg_id = int(data[b"user_tg_id"])
        delivery_id = int(data[b"delivery_id"])
        lead_id = int(data[b"lead_id"])
        brand = data[b"brand"].decode()
        city = data[b"city"].decode()
        summary = data[b"summary"].decode()
    except (KeyError, ValueError):
        logger.warning("Некорректные поля сообщения из стрима: %s", data)
        return

    text = lead_card_text(brand, city, summary)
    keyboard = lead_card_keyboard(delivery_id, lead_id)

    try:
        await bot.send_message(
            chat_id=user_tg_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        logger.info(
            "Карточка лида отправлена: tg_id=%s lead_id=%s delivery_id=%s",
            user_tg_id,
            lead_id,
            delivery_id,
        )
    except Exception:
        logger.exception(
            "Ошибка отправки карточки лида tg_id=%s lead_id=%s", user_tg_id, lead_id
        )


async def stream_worker(bot: Bot) -> None:
    """Читает Redis Stream leads:notify и рассылает карточки лидов."""
    r = aioredis.from_url(settings.redis_url, decode_responses=False)
    last_id = b"0"

    logger.info("Stream worker запущен, читаю %s", STREAM_KEY)

    while True:
        try:
            messages = await r.xread({STREAM_KEY: last_id}, block=5000, count=10)

            if not messages:
                continue

            for _stream, entries in messages:
                for msg_id, data in entries:
                    await _send_lead_card(bot, data)
                    last_id = msg_id

        except asyncio.CancelledError:
            logger.info("Stream worker остановлен.")
            break
        except Exception:
            logger.exception("Ошибка в stream worker, повтор через 5 сек.")
            await asyncio.sleep(5)

    await r.aclose()
