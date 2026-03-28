import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.api_client import client
from app.keyboards import BTN_ICEBREAKER, CB_ICEBREAKER

router = Router()
logger = logging.getLogger(__name__)


async def _run_icebreaker(tg_id: int, reply_fn) -> None:
    await reply_fn("⏳ Запускаю ледокол, ищу лиды для вас...")

    try:
        dispatched = await client.icebreaker(tg_id)
    except Exception:
        logger.exception("Ошибка запуска ледокола tg_id=%s", tg_id)
        await reply_fn("Произошла ошибка при запуске ледокола. Попробуйте позже.")
        return

    if dispatched == 0:
        await reply_fn(
            "😔 Нет новых лидов для отправки.\n\n"
            "Возможные причины:\n"
            "• Все доступные лиды уже были отправлены вам ранее\n"
            "• Ваш баланс пуст — пополните его, чтобы получать лиды"
        )
    else:
        n = dispatched
        leads_word = (
            "лид" if n % 10 == 1 and n % 100 != 11
            else "лида" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14
            else "лидов"
        )
        await reply_fn(
            f"🚀 <b>Ледокол запущен!</b>\n\n"
            f"Отправлено <b>{n} {leads_word}</b>. Карточки придут в ближайшие секунды — ожидайте!",
            parse_mode="HTML",
        )


@router.message(F.text == BTN_ICEBREAKER)
async def btn_icebreaker(message: Message) -> None:
    await _run_icebreaker(message.from_user.id, message.answer)


@router.callback_query(F.data == CB_ICEBREAKER)
async def cb_icebreaker(callback: CallbackQuery) -> None:
    await callback.answer()
    await _run_icebreaker(callback.from_user.id, callback.message.answer)
