import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from py4writers import API

from src.store import get_user_by_chat_id
from src.keyboards.order import get_order_keyboard

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
    api = API(login=user["login"], password=user["password"])
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
    """Показывает файлы заказа (пока заглушка)"""
    order_id = int(callback.data.split(":")[1])
    await callback.answer("📂 Files functionality coming soon!", show_alert=True)


@router.callback_query(F.data.startswith("order_take:"))
async def take_order(callback: CallbackQuery):
    """Взятие заказа (пока заглушка)"""
    order_id = int(callback.data.split(":")[1])
    await callback.answer("✅ Take order functionality coming soon!", show_alert=True)


@router.callback_query(F.data.startswith("order_back:"))
async def back_to_order(callback: CallbackQuery):
    """Возврат к карточке заказа"""
    order_id = int(callback.data.split(":")[1])
    # TODO: Восстановить оригинальное сообщение о заказе
    await callback.answer("⬅️ Back functionality coming soon!", show_alert=True)
