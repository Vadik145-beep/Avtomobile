import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.api_client import client
from app.keyboards import main_menu_keyboard, miniapp_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    tg_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    icebreaker_active = False
    try:
        user = await client.register_user(tg_id, username=username, first_name=first_name)
        limit_text = f"Ваш баланс: <b>{user.limit_count}</b> лимитов."
        icebreaker_active = user.icebreaker_active
    except Exception:
        logger.exception("Ошибка регистрации пользователя tg_id=%s", tg_id)
        limit_text = "Произошла ошибка при регистрации. Попробуйте позже."

    greeting = first_name or "Пользователь"
    await message.answer(
        f"Привет, {greeting}! 👋\n\n"
        "Добро пожаловать в <b>🚗 Лид Машина</b> — сервис автомобильных лидов.\n\n"
        f"{limit_text}\n\n"
        "Используйте кнопки ниже для навигации.",
        reply_markup=main_menu_keyboard(icebreaker_active=icebreaker_active),
        parse_mode="HTML",
    )
    await message.answer(
        "Пополнить баланс или посмотреть статистику:",
        reply_markup=miniapp_keyboard(),
    )
