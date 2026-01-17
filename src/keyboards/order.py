from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с кнопками управления заказом"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📂 Files", callback_data=f"order_files:{order_id}"),
        InlineKeyboardButton(text="📝 View", callback_data=f"order_view:{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Take", callback_data=f"order_take:{order_id}")
    )

    return builder.as_markup()


def get_confirm_take_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения взятия заказа"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Yes, I want take this order",
            callback_data=f"confirm_take:{order_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ No, I changed my mind",
            callback_data=f"order_back:{order_id}"
        )
    )

    return builder.as_markup()


def get_back_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data=f"order_back:{order_id}")
    )

    return builder.as_markup()
