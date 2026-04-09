import asyncio
import logging
import time

import redis.asyncio as aioredis
from aiogram import Bot

from app.config import settings
from app.keyboards import main_menu_keyboard
from app.templates import lead_card_text

logger = logging.getLogger(__name__)

STREAM_KEY = "leads:notify"
WORKER_LAST_ID_KEY = "bot:stream:last_id"

KEYBOARD_UPDATE_STREAM = "bot:keyboard_update"
KEYBOARD_UPDATE_LAST_ID_KEY = "bot:keyboard_update:last_id"


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
        recording_url = data.get(b"recording_url", b"").decode()
    except (KeyError, ValueError):
        logger.warning("Некорректные поля сообщения из стрима: %s", data)
        return

    text = lead_card_text(
        client_name=client_name,
        phone=phone,
        country_origin=country_origin,
        city=city,
        timing=timing,
        recording_url=recording_url,
    )

    send_after_raw = data.get(b"send_after", b"")
    if send_after_raw:
        delay = float(send_after_raw) - time.time()
        if delay > 0:
            await asyncio.sleep(delay)

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


async def _keyboard_update_worker(bot: Bot) -> None:
    """Читает Redis Stream bot:keyboard_update и обновляет клавиатуру пользователей."""
    r = aioredis.from_url(settings.redis_url, decode_responses=False)

    saved = await r.get(KEYBOARD_UPDATE_LAST_ID_KEY)
    last_id = saved if saved else b"$"

    logger.info("Keyboard update worker запущен, читаю %s с позиции %s", KEYBOARD_UPDATE_STREAM, last_id)

    while True:
        try:
            messages = await r.xread({KEYBOARD_UPDATE_STREAM: last_id}, block=5000, count=10)

            if not messages:
                continue

            for _stream, entries in messages:
                for msg_id, data in entries:
                    try:
                        tg_id = int(data[b"telegram_id"])
                        icebreaker_active = data.get(b"icebreaker_active", b"0") == b"1"
                        reason = data.get(b"reason", b"").decode()
                    except (KeyError, ValueError):
                        logger.warning("Некорректные поля keyboard_update: %s", data)
                        last_id = msg_id
                        await r.set(KEYBOARD_UPDATE_LAST_ID_KEY, last_id)
                        continue

                    if reason == "balance_empty":
                        status_text = (
                            "💳 <b>Баланс закончился — лидогенерация прекратила свою работу.</b>\n\n"
                            "Пополните баланс, чтобы снова получать лиды."
                        )
                    else:
                        status_text = (
                            "✅ Лидогенерация <b>запущена</b> администратором. Вы будете получать новые лиды."
                            if icebreaker_active
                            else "🛑 Лидогенерация <b>остановлена</b> администратором. Вы больше не будете получать лиды."
                        )
                    try:
                        await bot.send_message(
                            chat_id=tg_id,
                            text=status_text,
                            parse_mode="HTML",
                            reply_markup=main_menu_keyboard(icebreaker_active=icebreaker_active),
                        )
                        logger.info(
                            "Keyboard update отправлен: tg_id=%s icebreaker_active=%s",
                            tg_id,
                            icebreaker_active,
                        )
                    except Exception:
                        logger.exception(
                            "Ошибка отправки keyboard update tg_id=%s", tg_id
                        )

                    last_id = msg_id
                    await r.set(KEYBOARD_UPDATE_LAST_ID_KEY, last_id)

        except asyncio.CancelledError:
            logger.info("Keyboard update worker остановлен.")
            break
        except Exception:
            logger.exception("Ошибка в keyboard update worker, повтор через 5 сек.")
            await asyncio.sleep(5)

    await r.aclose()


async def _leads_worker(bot: Bot) -> None:
    """Читает Redis Stream leads:notify и рассылает карточки лидов."""
    r = aioredis.from_url(settings.redis_url, decode_responses=False)

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


async def stream_worker(bot: Bot) -> None:
    """Запускает оба воркера параллельно."""
    await asyncio.gather(
        _leads_worker(bot),
        _keyboard_update_worker(bot),
    )
