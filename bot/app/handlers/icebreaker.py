import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.api_client import client
from app.keyboards import (
    BTN_ICEBREAKER,
    BTN_STOP_ICEBREAKER,
    CB_ICEBREAKER,
    CB_STOP_ICEBREAKER,
    main_menu_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)


async def _run_icebreaker(tg_id: int, reply_fn) -> None:
    await reply_fn("⏳ Запускаю ледокол...")

    try:
        result = await client.icebreaker(tg_id)
    except Exception:
        logger.exception("Ошибка запуска ледокола tg_id=%s", tg_id)
        await reply_fn("Произошла ошибка при запуске ледокола. Попробуйте позже.")
        return

    if result.balance_empty:
        await reply_fn(
            "💳 <b>Баланс пуст</b>\n\n"
            "Пополните баланс, чтобы начать получать лиды.\n"
            "После пополнения нажмите <b>«🚀 Запустить ледокол»</b> снова.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(icebreaker_active=False),
        )
    elif result.dispatched == 0:
        await reply_fn(
            "✅ <b>Ледокол активирован!</b>\n\n"
            "Новых лидов в очереди пока нет, но как только они появятся — "
            "вы получите их автоматически.\n\n"
            "Оставайтесь на связи!",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(icebreaker_active=True),
        )
    else:
        n = result.dispatched
        leads_word = (
            "лид" if n % 10 == 1 and n % 100 != 11
            else "лида" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14
            else "лидов"
        )
        await reply_fn(
            f"🚀 <b>Ледокол запущен!</b>\n\n"
            f"Отправлено <b>{n} {leads_word}</b> из очереди. "
            f"Карточки придут в ближайшие секунды — ожидайте!\n\n"
            f"Новые лиды также будут приходить автоматически.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(icebreaker_active=True),
        )


async def _stop_icebreaker(tg_id: int, reply_fn) -> None:
    try:
        await client.stop_icebreaker(tg_id)
    except Exception:
        logger.exception("Ошибка остановки ледокола tg_id=%s", tg_id)
        await reply_fn("Произошла ошибка при остановке ледокола. Попробуйте позже.")
        return

    await reply_fn(
        "🛑 <b>Ледокол остановлен.</b>\n\n"
        "Вы больше не будете получать новые лиды.\n"
        "Чтобы возобновить — нажмите «🚀 Запустить ледокол».",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(icebreaker_active=False),
    )


@router.message(F.text == BTN_ICEBREAKER)
async def btn_icebreaker(message: Message) -> None:
    await _run_icebreaker(message.from_user.id, message.answer)


@router.callback_query(F.data == CB_ICEBREAKER)
async def cb_icebreaker(callback: CallbackQuery) -> None:
    await callback.answer()
    await _run_icebreaker(callback.from_user.id, callback.message.answer)


@router.message(F.text == BTN_STOP_ICEBREAKER)
async def btn_stop_icebreaker(message: Message) -> None:
    await _stop_icebreaker(message.from_user.id, message.answer)


@router.callback_query(F.data == CB_STOP_ICEBREAKER)
async def cb_stop_icebreaker(callback: CallbackQuery) -> None:
    await callback.answer()
    await _stop_icebreaker(callback.from_user.id, callback.message.answer)
