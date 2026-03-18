from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config import settings


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню с кнопкой открытия Mini App."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Открыть приложение",
                    web_app=WebAppInfo(url=settings.miniapp_url),
                )
            ]
        ]
    )


def lead_card_keyboard(delivery_id: int, lead_id: int) -> InlineKeyboardMarkup:
    """Клавиатура карточки лида с кнопкой открытия контакта."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📞 Открыть контакт",
                    callback_data=f"open_contact:{delivery_id}:{lead_id}",
                )
            ]
        ]
    )
