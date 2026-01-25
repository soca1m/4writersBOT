import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from src.utils.api_helper import get_api_class

from src.store import get_user_by_chat_id
from src.keyboards.order import get_order_keyboard, get_active_order_keyboard
from src.services.order_monitor import order_messages_cache
from src.workflows.order_workflow import process_order

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("order_view:"))
async def show_order_description(callback: CallbackQuery):
    """Показывает описание заказа при нажатии кнопки View"""
    order_id = int(callback.data.split(":")[1])
    logger.info(f"[DEBUG] Callback triggered, order_view: {order_id}")

    user = get_user_by_chat_id(callback.message.chat.id)
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    # Инициализация API-клиента и авторизация
    APIClass = get_api_class()
    api = APIClass(login=user["login"], password=user["password"])
    try:
        await api.login()
        logger.info("[DEBUG] Login successful")
    except Exception as e:
        await callback.answer(f"❌ Login failed: {e}", show_alert=True)
        logger.error(f"[DEBUG] Login failed: {e}")
        return

    # Получаем описание заказа
    description = await api.fetch_order_details(order_id)
    if description is None:
        text = "❌ No description available or failed to fetch order details."
    else:
        text = f"📝 <b>Order Description</b>\n\n{description}"

    logger.info(f"[DEBUG] Editing message with text: {text}")
    await callback.message.edit_text(
        text=text,
        reply_markup=get_order_keyboard(order_id)
    )
    await callback.answer()
    logger.info("[DEBUG] edit_text called")


@router.callback_query(F.data.startswith("order_files:"))
async def show_order_files(callback: CallbackQuery):
    """Показывает список файлов заказа"""
    order_index = int(callback.data.split(":")[1])

    user = get_user_by_chat_id(callback.message.chat.id)
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    # Инициализация API и авторизация
    APIClass = get_api_class()
    api = APIClass(login=user["login"], password=user["password"])
    try:
        await api.login()
        logger.info(f"Fetching files for order {order_index}")

        # Получаем список файлов
        files = await api.get_order_files(order_index)

        if not files:
            text = "📂 <b>Order Files</b>\n\n❌ No files attached to this order."
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

    except Exception as e:
        logger.error(f"Error fetching files for order {order_index}: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("order_take:"))
async def take_order(callback: CallbackQuery):
    """Взятие заказа в работу"""
    order_index = int(callback.data.split(":")[1])

    user = get_user_by_chat_id(callback.message.chat.id)
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    # Инициализация API и авторизация
    APIClass = get_api_class()
    api = APIClass(login=user["login"], password=user["password"])
    try:
        await api.login()
        logger.info(f"Taking order {order_index} for user {user['login']}")

        # Берём заказ
        success = await api.take_order(order_index)

        if success:
            await callback.answer("✅ Order taken successfully!", show_alert=True)
            # Обновляем сообщение
            await callback.message.edit_text(
                f"{callback.message.text}\n\n✅ <b>Order taken!</b>",
                reply_markup=None  # Убираем кнопки
            )
        else:
            await callback.answer("❌ Failed to take order. It may already be taken.", show_alert=True)

    except Exception as e:
        logger.error(f"Error taking order {order_index}: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("order_back:"))
async def back_to_order(callback: CallbackQuery):
    """Возврат к карточке заказа"""
    order_index = int(callback.data.split(":")[1])
    chat_id = callback.message.chat.id

    # Пытаемся восстановить оригинальный текст из кэша
    if chat_id in order_messages_cache and order_index in order_messages_cache[chat_id]:
        original_text = order_messages_cache[chat_id][order_index]

        await callback.message.edit_text(
            text=original_text,
            reply_markup=get_order_keyboard(order_index)
        )
        await callback.answer("⬅️ Returned to order card")
    else:
        await callback.answer("❌ Original message not found in cache", show_alert=True)
        logger.warning(f"Order {order_index} not found in cache for chat {chat_id}")


@router.callback_query(F.data.startswith("order_process:"))
async def process_order_with_ai(callback: CallbackQuery):
    """Обработка заказа через AI workflow"""
    order_index = int(callback.data.split(":")[1])

    user = get_user_by_chat_id(callback.message.chat.id)
    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    # Show processing message
    await callback.answer("🤖 Starting AI processing...")
    await callback.message.edit_text(
        f"{callback.message.text}\n\n🤖 <b>Processing with AI...</b>",
        reply_markup=None
    )

    # Get order details and files
    APIClass = get_api_class()
    api = APIClass(login=user["login"], password=user["password"])
    try:
        await api.login()
        logger.info(f"Processing order {order_index} with AI for user {user['login']}")

        # Get full order description
        description = await api.fetch_order_details(order_index)

        # Get order metadata from processing orders list
        processing_orders = await api.get_processing_orders()
        current_order = next((o for o in processing_orders if o.order_index == order_index), None)

        if not current_order:
            await callback.message.edit_text(
                "❌ <b>Error</b>\n\nOrder not found in processing orders",
                reply_markup=get_active_order_keyboard(order_index)
            )
            return

        # Get files
        files = await api.get_order_files(order_index)

        # Prepare order data for workflow
        order_data = {
            'order_id': current_order.order_id,
            'order_index': str(order_index),
            'description': description or "No description available",
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

        # Add files if available
        if files:
            logger.info(f"Found {len(files)} files for order {order_index}")
            # TODO: Download file contents when API supports it
            # order_data['files'] = [{'name': f.name, 'data': await api.download_file(f.id)} for f in files]

        # Process through AI workflow
        logger.info(f"Starting AI workflow for order {order_index}")
        final_state = await process_order(order_data, chat_id=callback.message.chat.id)

        if final_state.get('status') == 'completed':
            result_text = final_state.get('final_text', '')
            word_count = final_state.get('word_count', 0)
            ai_score = final_state.get('ai_score', 0)

            # Truncate result for display
            result_preview = result_text[:500] + "..." if len(result_text) > 500 else result_text

            await callback.message.edit_text(
                f"✅ <b>AI Processing Complete!</b>\n\n"
                f"📊 Word Count: {word_count}\n"
                f"🤖 AI Score: {ai_score:.1f}%\n\n"
                f"<b>Preview:</b>\n<code>{result_preview}</code>",
                reply_markup=get_active_order_keyboard(order_index)
            )

            # TODO: Upload result to platform when API supports it
            # await api.upload_order_result(order_index, result_text)

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
