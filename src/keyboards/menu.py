"""
Keyboards for main menu navigation
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Active Orders", callback_data="menu_active_orders"),
        InlineKeyboardButton(text="✅ Completed", callback_data="menu_completed")
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Late Orders", callback_data="menu_late_orders"),
        InlineKeyboardButton(text="🔄 Revisions", callback_data="menu_revisions")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistics", callback_data="menu_stats")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings")
    )

    return builder.as_markup()


def get_settings_menu(auto_collect_enabled: bool) -> InlineKeyboardMarkup:
    """Settings menu keyboard"""
    builder = InlineKeyboardBuilder()

    # Auto-collect toggle
    toggle_text = "✅ Auto-Collect: ON" if auto_collect_enabled else "❌ Auto-Collect: OFF"
    builder.row(
        InlineKeyboardButton(text=toggle_text, callback_data="settings_toggle_auto")
    )

    # Criteria configuration
    builder.row(
        InlineKeyboardButton(text="🎯 Configure Criteria", callback_data="settings_criteria")
    )

    # Back to main menu
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="menu_main")
    )

    return builder.as_markup()


def get_criteria_menu() -> InlineKeyboardMarkup:
    """Criteria configuration menu"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="💵 Price Range", callback_data="criteria_price"),
        InlineKeyboardButton(text="📄 Pages", callback_data="criteria_pages")
    )
    builder.row(
        InlineKeyboardButton(text="📝 Order Types", callback_data="criteria_types"),
        InlineKeyboardButton(text="🎓 Academic Level", callback_data="criteria_level")
    )
    builder.row(
        InlineKeyboardButton(text="📚 Subjects", callback_data="criteria_subjects"),
        InlineKeyboardButton(text="⏰ Deadline", callback_data="criteria_deadline")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Clear All", callback_data="criteria_clear")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Settings", callback_data="menu_settings")
    )

    return builder.as_markup()


def get_back_to_menu() -> InlineKeyboardMarkup:
    """Simple back to menu button"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="menu_main")
    )
    return builder.as_markup()


def get_workflow_details_keyboard(workflow_id: int) -> InlineKeyboardMarkup:
    """Keyboard for workflow details view"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 View Stages", callback_data=f"workflow_stages:{workflow_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu_main")
    )

    return builder.as_markup()
