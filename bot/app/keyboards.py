from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.config import settings

BTN_BALANCE = "💳 Баланс"
BTN_ICEBREAKER = "🚀 Запустить ледокол"

CB_BALANCE = "menu:balance"
CB_ICEBREAKER = "menu:icebreaker"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура главного меню с кнопками Баланс и Ледокол."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BALANCE)],
            [KeyboardButton(text=BTN_ICEBREAKER)],
        ],
        resize_keyboard=True,
        persistent=True,
        one_time_keyboard=False,
    )


def main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    """Объединённая inline-клавиатура: Баланс, Ледокол и Mini App."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_BALANCE, callback_data=CB_BALANCE)],
            [InlineKeyboardButton(text=BTN_ICEBREAKER, callback_data=CB_ICEBREAKER)],
            [
                InlineKeyboardButton(
                    text="📱 Открыть приложение",
                    web_app=WebAppInfo(url=settings.miniapp_url),
                )
            ],
        ]
    )


def miniapp_keyboard() -> InlineKeyboardMarkup:
    """Inline-кнопка открытия Mini App."""
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
