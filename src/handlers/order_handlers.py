"""
Order Handlers - Presentation Layer (Thin Controllers)
Only handle user interaction, delegate business logic to services
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from src.services.order_service import create_order_service_for_chat
from src.services.user_service import create_user_service
from src.formatters.message_formatters import OrderFormatter
from src.keyboards.order import get_order_keyboard
from src.services.order_monitor import order_messages_cache
from src.workflows.order_workflow import process_order

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("order_view:"))
async def show_order_description(callback: CallbackQuery):
    """Show order description"""
    order_index = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id

    order_service = create_order_service_for_chat(chat_id)
    if not order_service:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    async with order_service as service:
        order_data = await service.get_order_with_details(order_index)

        if not order_data['description']:
            text = "❌ No description available"
        else:
            text = f"📝 <b>Order Description</b>\n\n{order_data['description']}"

        await callback.message.edit_text(
            text=text,
            reply_markup=get_order_keyboard(order_index)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("order_files:"))
async def show_order_files(callback: CallbackQuery):
    """Show order files"""
    order_index = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id

    order_service = create_order_service_for_chat(chat_id)
    if not order_service:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    async with order_service as service:
        order_data = await service.get_order_with_details(order_index)
        files = order_data['files']

        if not files:
            text = "📂 <b>Order Files</b>\n\n❌ No files attached"
        else:
            text = f"📂 <b>Order Files</b> ({len(files)} file(s))\n\n"
            for idx, file in enumerate(files, 1):
                text += f"{idx}. 📄 <code>{file.name}</code>\n"
                text += f"   👤 Author: {file.author}\n"
                text += f"   📅 Date: {file.date}\n"
                text += f"   🆔 ID: {file.id}\n\n"

        await callback.message.edit_text(
            text=text,
            reply_markup=get_order_keyboard(order_index)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("order_take:"))
async def take_order(callback: CallbackQuery):
    """Take an order"""
    order_index = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id

    order_service = create_order_service_for_chat(chat_id)
    if not order_service:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    async with order_service as service:
        success = await service.take_order(order_index)

        if success:
            await callback.answer("✅ Order taken successfully!", show_alert=True)
            await callback.message.edit_text(
                f"{callback.message.text}\n\n✅ <b>Order taken!</b>",
                reply_markup=None
            )
        else:
            await callback.answer("❌ Failed to take order", show_alert=True)


@router.callback_query(F.data.startswith("order_back:"))
async def back_to_order(callback: CallbackQuery):
    """Go back to order card"""
    order_index = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id

    # Get cached original message
    if chat_id in order_messages_cache and order_index in order_messages_cache[chat_id]:
        original_text = order_messages_cache[chat_id][order_index]

        await callback.message.edit_text(
            text=original_text,
            reply_markup=get_order_keyboard(order_index)
        )
        await callback.answer("⬅️ Back to order")
    else:
        await callback.answer("❌ Cache expired", show_alert=True)


@router.callback_query(F.data.startswith("order_process:"))
async def process_order_with_ai(callback: CallbackQuery):
    """Process order with AI workflow"""
    order_index = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id

    await callback.answer("🤖 Starting AI processing...")
    await callback.message.edit_text(
        f"{callback.message.text}\n\n🤖 <b>Processing with AI...</b>",
        reply_markup=None
    )

    order_service = create_order_service_for_chat(chat_id)
    if not order_service:
        await callback.message.edit_text("❌ User not found!")
        return

    async with order_service as service:
        try:
            # Get order details
            order_data = await service.get_order_with_details(order_index)

            # Get order metadata (would need to fetch from processing orders)
            orders_dict = await service.get_all_orders_by_type()
            processing_orders = orders_dict['processing']

            current_order = next(
                (o for o in processing_orders if o.order_index == order_index),
                None
            )

            if not current_order:
                await callback.message.edit_text(
                    "❌ <b>Error</b>\n\nOrder not found in processing",
                    reply_markup=get_active_order_keyboard(order_index)
                )
                return

            # Prepare workflow data
            workflow_data = {
                'order_id': current_order.order_id,
                'order_index': str(order_index),
                'description': order_data['description'] or "",
                'pages': current_order.pages,
                'deadline': current_order.remaining,
                'title': current_order.title,
                'subject': current_order.subject,
                'order_type': current_order.order_type,
                'academic_level': current_order.academic_level,
                'style': current_order.style,
                'sources': current_order.sources,
                'files': []
            }

            # Run workflow
            logger.info(f"Starting AI workflow for order {order_index}")
            final_state = await process_order(workflow_data, chat_id=chat_id)

            if final_state.get('status') == 'completed':
                result_text = final_state.get('final_text', '')
                word_count = final_state.get('word_count', 0)
                ai_score = final_state.get('ai_score', 0)

                result_preview = result_text[:500] + "..." if len(result_text) > 500 else result_text

                await callback.message.edit_text(
                    f"✅ <b>AI Processing Complete!</b>\n\n"
                    f"📊 Word Count: {word_count}\n"
                    f"🤖 AI Score: {ai_score:.1f}%\n\n"
                    f"<b>Preview:</b>\n<code>{result_preview}</code>",
                    reply_markup=get_active_order_keyboard(order_index)
                )
            else:
                error_msg = final_state.get('error', 'Unknown error')
                await callback.message.edit_text(
                    f"❌ <b>AI Processing Failed</b>\n\n"
                    f"Error: {error_msg}",
                    reply_markup=get_active_order_keyboard(order_index)
                )

        except Exception as e:
            logger.error(f"Error processing order {order_index} with AI: {e}")
            await callback.message.edit_text(
                f"❌ <b>Error</b>\n\n{str(e)}",
                reply_markup=get_active_order_keyboard(order_index)
            )


# Import keyboard functions (should be in keyboards module)
def get_active_order_keyboard(order_index: int):
    """Temporary keyboard function"""
    from src.keyboards.order import get_active_order_keyboard as kb
    return kb(order_index)