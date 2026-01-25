"""
Message-based menu handlers - Clean architecture
"""
import logging
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from py4writers import Order
from typing import List

from src.store import get_user_by_chat_id
from src.db.database import get_user_settings, get_workflow_stats
from src.services.api_service import create_api_service

router = Router()
logger = logging.getLogger(__name__)

# Cache
completed_orders_cache = {}
message_ids_cache = {}
ORDERS_PER_PAGE = 3


def format_order_card(order: Order, index: int, prefix: str = "✅ Completed") -> str:
    """Format order as a card"""
    return (
        f"{prefix} <b>Order #{index}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> <code>{order.order_id}</code>\n"
        f"📝 <b>Title:</b> <code>{order.title}</code>\n"
        f"📚 <b>Subject:</b> <code>{order.subject}</code>\n"
        f"📄 <b>Type:</b> <code>{order.order_type}</code>\n"
        f"🎓 <b>Level:</b> <code>{order.academic_level}</code>\n"
        f"🖋 <b>Style:</b> <code>{order.style}</code>\n"
        f"📄 <b>Pages:</b> <code>{order.pages}</code>\n"
        f"🔎 <b>Sources:</b> <code>{order.sources}</code>\n"
        f"💵 <b>Total:</b> $<code>{order.total}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def get_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Create pagination keyboard"""
    builder = InlineKeyboardBuilder()
    buttons = []

    if page > 0:
        buttons.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"completed_page:{page-1}"))

    buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))

    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"completed_page:{page+1}"))

    if buttons:
        builder.row(*buttons)

    return builder.as_markup()


async def delete_old_messages(bot: Bot, chat_id: int):
    """Delete old pagination messages"""
    if chat_id in message_ids_cache:
        cache = message_ids_cache[chat_id]

        for msg_id in cache.get("message_ids", []):
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception as e:
                logger.debug(f"Failed to delete message {msg_id}: {e}")

        if "control_id" in cache:
            try:
                await bot.delete_message(chat_id, cache["control_id"])
            except Exception:
                pass

        message_ids_cache.pop(chat_id, None)


async def show_active_orders(message: Message):
    """Show active/processing orders"""
    user = get_user_by_chat_id(message.chat.id)
    if not user:
        await message.answer("❌ User not found!")
        return

    async with create_api_service(user["login"], user["password"]) as api:
        orders = await api.get_processing_orders()

        if not orders or len(orders) == 0:
            await message.answer("📋 <b>Active Orders</b>\n\n❌ No active orders")
        else:
            text = f"📋 <b>Active Orders</b> ({len(orders)})\n\n"
            for idx, order in enumerate(orders, 1):
                text += f"{idx}. <b>{order.title}</b>\n"
                text += f"   💵 ${order.total} | 📄 {order.pages}p | ⏰ {order.remaining}\n"
                text += f"   🆔 #{order.order_index}\n\n"

            await message.answer(text)


async def show_completed_orders(message: Message, page: int = 0):
    """Show completed orders with pagination"""
    user = get_user_by_chat_id(message.chat.id)
    if not user:
        await message.answer("❌ User not found!")
        return

    await delete_old_messages(message.bot, message.chat.id)

    async with create_api_service(user["login"], user["password"]) as api:
        orders = await api.get_completed_orders()

        if not orders or len(orders) == 0:
            await message.answer("✅ <b>Completed Orders</b>\n\n❌ No completed orders")
            return

        completed_orders_cache[message.chat.id] = orders

        total_pages = (len(orders) + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE
        page = min(page, total_pages - 1)

        start_idx = page * ORDERS_PER_PAGE
        end_idx = min(start_idx + ORDERS_PER_PAGE, len(orders))
        page_orders = orders[start_idx:end_idx]

        message_ids = []
        for idx, order in enumerate(page_orders, start=start_idx + 1):
            card_text = format_order_card(order, idx, "✅ Completed")
            msg = await message.answer(card_text)
            message_ids.append(msg.message_id)

        if total_pages > 1:
            summary = f"📄 Page {page+1}/{total_pages} | Total: {len(orders)} orders"
            control_msg = await message.answer(summary, reply_markup=get_pagination_keyboard(page, total_pages))

            message_ids_cache[message.chat.id] = {
                "message_ids": message_ids,
                "control_id": control_msg.message_id
            }
        else:
            message_ids_cache[message.chat.id] = {
                "message_ids": message_ids,
                "control_id": None
            }


async def show_late_orders(message: Message):
    """Show late orders"""
    user = get_user_by_chat_id(message.chat.id)
    if not user:
        await message.answer("❌ User not found!")
        return

    async with create_api_service(user["login"], user["password"]) as api:
        orders = await api.get_late_orders()

        if not orders or len(orders) == 0:
            await message.answer("⏰ <b>Late Orders</b>\n\n✅ No late orders")
        else:
            text = f"⏰ <b>Late Orders</b> ({len(orders)})\n\n"
            for idx, order in enumerate(orders, 1):
                text += f"{idx}. <b>{order.title}</b>\n"
                text += f"   💵 ${order.total} | 📄 {order.pages}p\n"
                text += f"   🆔 #{order.order_index}\n\n"

            await message.answer(text)


async def show_revisions(message: Message):
    """Show revision orders"""
    user = get_user_by_chat_id(message.chat.id)
    if not user:
        await message.answer("❌ User not found!")
        return

    async with create_api_service(user["login"], user["password"]) as api:
        orders = await api.get_revision_orders()

        if not orders or len(orders) == 0:
            await message.answer("🔄 <b>Revision Orders</b>\n\n✅ No revisions")
        else:
            text = f"🔄 <b>Revision Orders</b> ({len(orders)})\n\n"
            for idx, order in enumerate(orders, 1):
                text += f"{idx}. <b>{order.title}</b>\n"
                text += f"   💵 ${order.total} | 📄 {order.pages}p | ⏰ {order.remaining}\n"
                text += f"   🆔 #{order.order_index}\n\n"

            await message.answer(text)


async def show_statistics(message: Message):
    """Show full statistics"""
    chat_id = message.chat.id
    stats = get_workflow_stats(chat_id)

    user = get_user_by_chat_id(chat_id)
    if not user:
        await message.answer("❌ User not found!")
        return

    async with create_api_service(user["login"], user["password"]) as api:
        active_orders = await api.get_processing_orders()
        completed_orders = await api.get_completed_orders()
        late_orders = await api.get_late_orders()
        revision_orders = await api.get_revision_orders()

        active_count = len(active_orders) if active_orders else 0
        completed_count = len(completed_orders) if completed_orders else 0
        late_count = len(late_orders) if late_orders else 0
        revision_count = len(revision_orders) if revision_orders else 0

        text = "📊 <b>Full Statistics</b>\n\n"

        text += "━━━ <b>Orders Overview</b> ━━━\n"
        text += f"📋 Active Orders: {active_count}\n"
        text += f"✅ Completed: {completed_count}\n"
        text += f"⏰ Late: {late_count}\n"
        text += f"🔄 Revisions: {revision_count}\n\n"

        text += "━━━ <b>AI Workflow Stats</b> ━━━\n"
        text += f"🔢 Total Workflows: {stats['total_workflows']}\n"
        text += f"✅ Completed: {stats['completed_workflows']}\n"
        text += f"❌ Failed: {stats['failed_workflows']}\n"
        text += f"📝 Total Words: {stats['total_words_generated']:,}\n"
        text += f"🤖 Avg AI Score: {stats['avg_ai_score']:.1f}%\n"

        if stats['last_workflow_at']:
            text += f"\n⏰ Last Workflow: {stats['last_workflow_at'][:16]}"

        await message.answer(text)


async def show_settings(message: Message):
    """Show settings menu"""
    chat_id = message.chat.id
    settings = get_user_settings(chat_id)

    auto_enabled = settings["auto_collect_enabled"]
    max_orders = settings["max_orders"]
    criteria = settings.get("criteria", {})

    text = "⚙️ <b>Settings</b>\n\n"
    text += f"Auto-Collection: {'✅ Enabled' if auto_enabled else '❌ Disabled'}\n"
    text += f"Max Orders: {max_orders}\n\n"

    text += "━━━ <b>Criteria</b> ━━━\n"

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
        text += "❌ No criteria set\n"

    from src.keyboards.menu import get_settings_menu
    await message.answer(text, reply_markup=get_settings_menu(auto_enabled))


@router.callback_query(lambda c: c.data.startswith("completed_page:"))
async def pagination_handler(callback: CallbackQuery):
    """Handle pagination for completed orders"""
    page = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id

    if chat_id not in completed_orders_cache:
        await callback.answer("❌ Cache expired, please refresh", show_alert=True)
        return

    await delete_old_messages(callback.bot, chat_id)

    orders = completed_orders_cache[chat_id]
    total_pages = (len(orders) + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE

    start_idx = page * ORDERS_PER_PAGE
    end_idx = min(start_idx + ORDERS_PER_PAGE, len(orders))
    page_orders = orders[start_idx:end_idx]

    message_ids = []
    for idx, order in enumerate(page_orders, start=start_idx + 1):
        card_text = format_order_card(order, idx, "✅ Completed")
        msg = await callback.message.answer(card_text)
        message_ids.append(msg.message_id)

    summary = f"📄 Page {page+1}/{total_pages} | Total: {len(orders)} orders"
    control_msg = await callback.message.answer(summary, reply_markup=get_pagination_keyboard(page, total_pages))

    message_ids_cache[chat_id] = {
        "message_ids": message_ids,
        "control_id": control_msg.message_id
    }

    await callback.answer(f"Page {page+1}/{total_pages}")
