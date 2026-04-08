import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.api_client import client
from app.keyboards import BTN_BALANCE, CB_BALANCE, main_menu_keyboard, miniapp_keyboard

router = Router()
logger = logging.getLogger(__name__)


async def _send_balance(tg_id: int, reply_fn) -> None:
    try:
        user = await client.get_user(tg_id)
        if user is None:
            await reply_fn("Вы ещё не зарегистрированы. Отправьте /start для регистрации.")
            return

        n = user.limit_count
        leads_text = f"<b>{n}</b> {'лид' if n % 10 == 1 and n % 100 != 11 else 'лида' if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 'лидов'}"

        await reply_fn(
            f"💳 <b>Ваш баланс:</b> {n} лимитов.\n\n"
            f"На этот баланс вам придёт {leads_text}.\n\n"
            "Нажмите кнопку ниже, чтобы пополнить баланс:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Ошибка получения баланса tg_id=%s", tg_id)
        await reply_fn("Ошибка при получении баланса. Попробуйте позже.")


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    await _send_balance(message.from_user.id, message.answer)


@router.message(F.text == BTN_BALANCE)
async def btn_balance(message: Message) -> None:
    await _send_balance(message.from_user.id, message.answer)


@router.callback_query(F.data == CB_BALANCE)
async def cb_balance(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_balance(callback.from_user.id, callback.message.answer)
