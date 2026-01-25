"""
Menu handlers for navigation and settings
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from src.utils.api_helper import get_api_class

from src.store import get_user_by_chat_id
from src.db.database import (
    get_user_settings,
    toggle_auto_collect,
    get_workflow_stats,
    get_workflows_by_status,
    get_workflow_details,
    update_criteria
)
from src.keyboards.menu import (
    get_main_menu,
    get_settings_menu,
    get_criteria_menu,
    get_back_to_menu,
    get_workflow_details_keyboard
)

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("menu"))
async def show_menu(message: Message):
    """Show main menu"""
    await message.answer(
        "📱 <b>Main Menu</b>\n\n"
        "Choose an option:",
        reply_markup=get_main_menu()
    )


@router.callback_query(F.data == "menu_main")
async def menu_main(callback: CallbackQuery):
    """Back to main menu"""
    await callback.message.edit_text(
        "📱 <b>Main Menu</b>\n\n"
        "Choose an option:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


# ==================== ORDER LISTS ====================

@router.callback_query(F.data == "menu_active_orders")
async def menu_active_orders(callback: CallbackQuery):
    """Show active/processing orders"""
    user = get_user_by_chat_id(callback.message.chat.id)
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    APIClass = get_api_class()
    api = APIClass(login=user["login"], password=user["password"])
    try:
        await api.login()
        orders = await api.get_processing_orders()

        if not orders or len(orders) == 0:
            text = "📋 <b>Active Orders</b>\n\n❌ No active orders"
        else:
            text = f"📋 <b>Active Orders</b> ({len(orders)})\n\n"
            for idx, order in enumerate(orders, 1):
                text += f"{idx}. <b>{order.title}</b>\n"
                text += f"   💵 ${order.total} | 📄 {order.pages}p | ⏰ {order.remaining}\n"
                text += f"   🆔 #{order.order_index}\n\n"

        await callback.message.edit_text(
            text=text,
            reply_markup=get_back_to_menu()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching active orders: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        await api.close()


@router.callback_query(F.data == "menu_completed")
async def menu_completed(callback: CallbackQuery):
    """Show completed orders"""
    user = get_user_by_chat_id(callback.message.chat.id)
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    APIClass = get_api_class()
    api = APIClass(login=user["login"], password=user["password"])
    try:
        await api.login()
        orders = await api.get_completed_orders()

        if not orders or len(orders) == 0:
            text = "✅ <b>Completed Orders</b>\n\n❌ No completed orders"
        else:
            text = f"✅ <b>Completed Orders</b> ({len(orders)})\n\n"
            for idx, order in enumerate(orders, 1):
                text += f"{idx}. <b>{order.title}</b>\n"
                text += f"   💵 ${order.total} | 📄 {order.pages}p\n"
                text += f"   🆔 #{order.order_index}\n\n"

        await callback.message.edit_text(
            text=text,
            reply_markup=get_back_to_menu()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching completed orders: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        await api.close()


@router.callback_query(F.data == "menu_late_orders")
async def menu_late_orders(callback: CallbackQuery):
    """Show late orders"""
    user = get_user_by_chat_id(callback.message.chat.id)
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    APIClass = get_api_class()
    api = APIClass(login=user["login"], password=user["password"])
    try:
        await api.login()
        orders = await api.get_late_orders()

        if not orders or len(orders) == 0:
            text = "⏰ <b>Late Orders</b>\n\n✅ No late orders"
        else:
            text = f"⏰ <b>Late Orders</b> ({len(orders)})\n\n"
            for idx, order in enumerate(orders, 1):
                text += f"{idx}. <b>{order.title}</b>\n"
                text += f"   💵 ${order.total} | 📄 {order.pages}p\n"
                text += f"   🆔 #{order.order_index}\n\n"

        await callback.message.edit_text(
            text=text,
            reply_markup=get_back_to_menu()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching late orders: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        await api.close()


@router.callback_query(F.data == "menu_revisions")
async def menu_revisions(callback: CallbackQuery):
    """Show revision orders"""
    user = get_user_by_chat_id(callback.message.chat.id)
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    APIClass = get_api_class()
    api = APIClass(login=user["login"], password=user["password"])
    try:
        await api.login()
        orders = await api.get_revision_orders()

        if not orders or len(orders) == 0:
            text = "🔄 <b>Revision Orders</b>\n\n✅ No revisions"
        else:
            text = f"🔄 <b>Revision Orders</b> ({len(orders)})\n\n"
            for idx, order in enumerate(orders, 1):
                text += f"{idx}. <b>{order.title}</b>\n"
                text += f"   💵 ${order.total} | 📄 {order.pages}p | ⏰ {order.remaining}\n"
                text += f"   🆔 #{order.order_index}\n\n"

        await callback.message.edit_text(
            text=text,
            reply_markup=get_back_to_menu()
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error fetching revision orders: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        await api.close()


# ==================== STATISTICS ====================

@router.callback_query(F.data == "menu_stats")
async def menu_stats(callback: CallbackQuery):
    """Show workflow statistics"""
    chat_id = callback.message.chat.id
    stats = get_workflow_stats(chat_id)

    text = "📊 <b>Your Statistics</b>\n\n"
    text += f"🔢 Total Workflows: {stats['total_workflows']}\n"
    text += f"✅ Completed: {stats['completed_workflows']}\n"
    text += f"❌ Failed: {stats['failed_workflows']}\n"
    text += f"📝 Total Words: {stats['total_words_generated']:,}\n"
    text += f"🤖 Avg AI Score: {stats['avg_ai_score']:.1f}%\n"

    if stats['last_workflow_at']:
        text += f"\n⏰ Last: {stats['last_workflow_at'][:16]}"

    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_menu()
    )
    await callback.answer()


# ==================== SETTINGS ====================

@router.callback_query(F.data == "menu_settings")
async def menu_settings(callback: CallbackQuery):
    """Show settings menu"""
    chat_id = callback.message.chat.id
    settings = get_user_settings(chat_id)

    auto_enabled = settings["auto_collect_enabled"]
    max_orders = settings["max_orders"]

    text = "⚙️ <b>Settings</b>\n\n"
    text += f"Auto-Collection: {'✅ Enabled' if auto_enabled else '❌ Disabled'}\n"
    text += f"Max Orders: {max_orders}\n"

    await callback.message.edit_text(
        text=text,
        reply_markup=get_settings_menu(auto_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "settings_toggle_auto")
async def settings_toggle_auto(callback: CallbackQuery):
    """Toggle auto-collection"""
    chat_id = callback.message.chat.id
    new_state = toggle_auto_collect(chat_id)

    settings = get_user_settings(chat_id)
    max_orders = settings["max_orders"]

    status = "✅ Enabled" if new_state else "❌ Disabled"

    text = "⚙️ <b>Settings</b>\n\n"
    text += f"Auto-Collection: {status}\n"
    text += f"Max Orders: {max_orders}\n"

    await callback.message.edit_text(
        text=text,
        reply_markup=get_settings_menu(new_state)
    )
    await callback.answer(f"Auto-collection {status}")


@router.callback_query(F.data == "settings_criteria")
async def settings_criteria(callback: CallbackQuery):
    """Show criteria configuration menu"""
    chat_id = callback.message.chat.id
    settings = get_user_settings(chat_id)
    criteria = settings.get("criteria", {})

    text = "🎯 <b>Order Criteria</b>\n\n"

    if criteria.get("min_price") or criteria.get("max_price"):
        text += f"💵 Price: ${criteria.get('min_price', 0)} - ${criteria.get('max_price', '∞')}\n"

    if criteria.get("min_pages") or criteria.get("max_pages"):
        text += f"📄 Pages: {criteria.get('min_pages', 0)} - {criteria.get('max_pages', '∞')}\n"

    if criteria.get("order_types"):
        text += f"📝 Types: {', '.join(criteria['order_types'][:3])}\n"

    if criteria.get("academic_levels"):
        text += f"🎓 Levels: {', '.join(criteria['academic_levels'][:3])}\n"

    if criteria.get("subjects"):
        text += f"📚 Subjects: {', '.join(criteria['subjects'][:3])}\n"

    if criteria.get("min_deadline_hours"):
        text += f"⏰ Min Deadline: {criteria['min_deadline_hours']}h\n"

    if not any(criteria.values()):
        text += "❌ No criteria set - will accept any orders\n"

    text += "\nSelect a criterion to configure:"

    await callback.message.edit_text(
        text=text,
        reply_markup=get_criteria_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "criteria_clear")
async def criteria_clear(callback: CallbackQuery):
    """Clear all criteria"""
    chat_id = callback.message.chat.id

    update_criteria(chat_id, {
        "min_price": None,
        "max_price": None,
        "order_types": [],
        "academic_levels": [],
        "subjects": [],
        "min_pages": None,
        "max_pages": None,
        "min_deadline_hours": None
    })

    await callback.answer("✅ All criteria cleared")

    # Show updated criteria menu
    await settings_criteria(callback)


# Criteria editing callbacks - these will prompt user to send a message
@router.callback_query(F.data.startswith("criteria_"))
async def criteria_edit_prompt(callback: CallbackQuery):
    """Prompt user to configure specific criterion"""
    criterion = callback.data.split("_")[1]

    prompts = {
        "price": "💵 Send min and max price separated by space (e.g. `5 20`)",
        "pages": "📄 Send min and max pages separated by space (e.g. `1 5`)",
        "types": "📝 Send order types separated by commas (e.g. `Essay, Research Paper, Discussion Board Post`)",
        "level": "🎓 Send academic levels separated by commas (e.g. `College, High School`)",
        "subjects": "📚 Send subjects separated by commas (e.g. `Nursing, History, Psychology`)",
        "deadline": "⏰ Send minimum deadline in hours (e.g. `12`)"
    }

    if criterion in prompts:
        await callback.answer(prompts[criterion], show_alert=True)
