from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()


def get_reply_keyboard() -> ReplyKeyboardMarkup:
    """Reply keyboard with all menu options"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Active Orders"), KeyboardButton(text="✅ Completed")],
            [KeyboardButton(text="⏰ Late Orders"), KeyboardButton(text="🔄 Revisions")],
            [KeyboardButton(text="📊 Statistics"), KeyboardButton(text="⚙️ Settings")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        f"👋 <b>Welcome, {message.from_user.first_name}!</b>\n\n"
        "🤖 <b>4writers AI Assistant Bot</b>\n\n"
        "This bot helps you:\n"
        "• 📋 Monitor and manage orders\n"
        "• 🤖 Process orders with AI workflow\n"
        "• ⚙️ Auto-collect orders by criteria\n"
        "• 📊 Track your statistics\n\n"
        "Use the menu buttons below:",
        reply_markup=get_reply_keyboard()
    )


# Forward button presses to menu handlers
@router.message(F.text == "📋 Active Orders")
async def active_orders_button(message: Message):
    """Forward to active orders handler"""
    from src.handlers.menu_message import show_active_orders
    await show_active_orders(message)


@router.message(F.text == "✅ Completed")
async def completed_button(message: Message):
    """Forward to completed orders handler"""
    from src.handlers.menu_message import show_completed_orders
    await show_completed_orders(message)


@router.message(F.text == "⏰ Late Orders")
async def late_orders_button(message: Message):
    """Forward to late orders handler"""
    from src.handlers.menu_message import show_late_orders
    await show_late_orders(message)


@router.message(F.text == "🔄 Revisions")
async def revisions_button(message: Message):
    """Forward to revisions handler"""
    from src.handlers.menu_message import show_revisions
    await show_revisions(message)


@router.message(F.text == "📊 Statistics")
async def statistics_button(message: Message):
    """Forward to statistics handler"""
    from src.handlers.menu_message import show_statistics
    await show_statistics(message)


@router.message(F.text == "⚙️ Settings")
async def settings_button(message: Message):
    """Forward to settings handler"""
    from src.handlers.menu_message import show_settings
    await show_settings(message)
