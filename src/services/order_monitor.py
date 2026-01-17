import asyncio
import logging
from typing import Optional
from py4writers import API, Order
from py4writers.exceptions import NetworkError, AuthenticationError

from src.store import get_users
from src.keyboards.order import get_order_keyboard

logger = logging.getLogger(__name__)

# Хранилище предыдущих заказов: {user_login: {order_id: title}}
previous_orders = {}


def format_new_order(order: Order) -> str:
    """Форматирует сообщение о новом заказе"""
    return (
        "🔔 <b>Поступил новый заказ!</b> "
        f"{order.order_type} ${order.total}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> <code>{order.order_id}</code>\n"
        f"📝 <b>Title:</b> <code>{order.title}</code>\n"
        f"📚 <b>Subject:</b> <code>{order.subject}</code>\n"
        f"⌛️ <b>Deadline:</b> <code>{order.remaining}</code>\n"
        f"📄 <b>Type:</b> <code>{order.order_type}</code>\n"
        f"🎓 <b>Level:</b> <code>{order.academic_level}</code>\n"
        f"🖋 <b>Style:</b> <code>{order.style}</code>\n"
        f"📄 <b>Pages:</b> <code>{order.pages}</code>\n"
        f"🔎 <b>Sources:</b> <code>{order.sources}</code>\n"
        f"💵 <b>Total:</b> $<code>{order.total}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def format_removed_order(order_id: str, title: Optional[str] = None) -> str:
    """Форматирует сообщение об удалении заказа"""
    if title:
        return f"❌ Заказ <b>{title}</b> больше недоступен."
    return f"❌ Заказ {order_id} больше недоступен."


async def process_user(bot, api: API, user: dict):
    """Обрабатывает заказы пользователя"""
    user_login = user["login"]
    chat_id = user["id"]

    try:
        await api.login()

        current_orders = await api.get_orders()

        if current_orders is None:
            logger.error(f"❌ API вернул None для пользователя {user_login}")
            return

        # Создаём словарь {order_id: title} для текущих заказов
        current_order_dict = {
            order.order_id: order.title for order in current_orders if order
        }

        # Получаем предыдущие заказы пользователя
        old_order_dict = previous_orders.get(user_login, {})

        # Определяем новые и пропавшие заказы
        new_orders = set(current_order_dict.keys()) - set(old_order_dict.keys())
        removed_orders = set(old_order_dict.keys()) - set(current_order_dict.keys())

        # Отправляем уведомления о новых заказах
        for order in current_orders:
            if order and order.order_id in new_orders:
                await bot.send_message(
                    chat_id=chat_id,
                    text=format_new_order(order),
                    reply_markup=get_order_keyboard(order.order_id)
                )

        # Отправляем уведомления об удалённых заказах
        for order_id in removed_orders:
            title = old_order_dict.get(order_id, None)
            await bot.send_message(
                chat_id=chat_id,
                text=format_removed_order(order_id, title)
            )

        # Обновляем previous_orders
        previous_orders[user_login] = current_order_dict

    except NetworkError as e:
        logger.warning(f"⚠️  Сетевая ошибка для {user_login}: {e}. Пропускаем итерацию.")
    except AuthenticationError as e:
        logger.error(f"❌ Ошибка авторизации для {user_login}: {e}")
    except Exception as e:
        logger.error(f"❌ Неизвестная ошибка для {user_login}: {e}")


async def start_monitoring(bot):
    """Основная корутина мониторинга заказов"""
    logger.info("🔄 Order monitoring started")

    while True:
        for user in get_users():
            # Используем context manager для правильного управления ресурсами
            async with API(login=user["login"], password=user["password"]) as api:
                await process_user(bot, api, user)
            await asyncio.sleep(5)
