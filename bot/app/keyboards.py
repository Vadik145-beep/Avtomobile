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
BTN_STOP_ICEBREAKER = "🛑 Остановить ледокол"

CB_BALANCE = "menu:balance"
CB_ICEBREAKER = "menu:icebreaker"
CB_STOP_ICEBREAKER = "menu:stop_icebreaker"


def main_menu_keyboard(icebreaker_active: bool = False) -> ReplyKeyboardMarkup:
    """Reply-клавиатура главного меню. Показывает кнопку старта или остановки ледокола."""
    ice_btn = BTN_STOP_ICEBREAKER if icebreaker_active else BTN_ICEBREAKER
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BALANCE)],
            [KeyboardButton(text=ice_btn)],
        ],
        resize_keyboard=True,
        persistent=True,
        one_time_keyboard=False,
    )


def main_menu_inline_keyboard(icebreaker_active: bool = False) -> InlineKeyboardMarkup:
    """Объединённая inline-клавиатура: Баланс, Ледокол и Mini App."""
    ice_text = BTN_STOP_ICEBREAKER if icebreaker_active else BTN_ICEBREAKER
    ice_cb = CB_STOP_ICEBREAKER if icebreaker_active else CB_ICEBREAKER
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_BALANCE, callback_data=CB_BALANCE)],
            [InlineKeyboardButton(text=ice_text, callback_data=ice_cb)],
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
