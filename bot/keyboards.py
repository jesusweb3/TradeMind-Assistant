"""
Клавиатуры и меню бота.
"""

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Новая сделка")],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура подтверждения."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
            ],
        ]
    )
    return keyboard


def get_done_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для завершения загрузки скриншотов."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Готово")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Отправьте скриншоты или нажмите Готово",
    )
    return keyboard
