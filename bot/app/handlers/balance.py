import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.api_client import client
from app.keyboards import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    tg_id = message.from_user.id

    try:
        user = await client.get_user(tg_id)
        if user is None:
            await message.answer(
                "Вы ещё не зарегистрированы. Отправьте /start для регистрации."
            )
            return

        await message.answer(
            f"💳 Ваш баланс: <b>{user.limit_count}</b> лимитов.\n\n"
            "Чтобы пополнить — откройте приложение.",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Ошибка получения баланса tg_id=%s", tg_id)
        await message.answer("Ошибка при получении баланса. Попробуйте позже.")
