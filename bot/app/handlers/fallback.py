import logging

from aiogram import Router
from aiogram.types import Message

from app.keyboards import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message()
async def fallback_handler(message: Message) -> None:
    logger.debug("Fallback handler: tg_id=%s text=%r", message.from_user.id, message.text)
    await message.answer(
        "Используйте кнопки меню для навигации.",
        reply_markup=main_menu_keyboard(),
    )
