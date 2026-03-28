import logging

import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.api_client import client
from app.keyboards import main_menu_inline_keyboard
from app.templates import contact_opened_text

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("open_contact:"))
async def callback_open_contact(callback: CallbackQuery) -> None:
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.message.answer("Некорректный запрос.")
        return

    _, delivery_id_str, lead_id_str = parts
    try:
        delivery_id = int(delivery_id_str)
        lead_id = int(lead_id_str)
    except ValueError:
        await callback.message.answer("Некорректный запрос.")
        return

    tg_id = callback.from_user.id

    try:
        result = await client.open_contact(tg_id, lead_id, delivery_id)
        recording_url = None
        await callback.message.answer(
            contact_opened_text(result.phone, recording_url),
            parse_mode="HTML",
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 402:
            await callback.message.answer(
                "❌ Недостаточно лимитов.\n\n"
                "Пополните баланс в приложении 👇",
                reply_markup=main_menu_inline_keyboard(),
            )
        elif exc.response.status_code == 409:
            await callback.message.answer(
                "⚠️ Контакт уже занят другим пользователем."
            )
        else:
            logger.exception(
                "Ошибка открытия контакта tg_id=%s lead_id=%s", tg_id, lead_id
            )
            await callback.message.answer("Произошла ошибка. Попробуйте позже.")
    except Exception:
        logger.exception(
            "Неожиданная ошибка открытия контакта tg_id=%s lead_id=%s", tg_id, lead_id
        )
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")
