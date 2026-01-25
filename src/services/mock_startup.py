"""
Mock startup service - sends test orders on bot start in mock mode
"""
import logging
from aiogram import Bot
from src.store import get_users
from src.utils.mock_data import get_mock_orders
from src.keyboards.order import get_order_keyboard

logger = logging.getLogger(__name__)


async def send_mock_orders_on_startup(bot: Bot):
    """Send mock available orders to all users on startup"""
    logger.info("📬 Sending mock orders on startup...")

    mock_orders = get_mock_orders()
    users = get_users()

    for user in users:
        chat_id = user["id"]

        try:
            await bot.send_message(
                chat_id=chat_id,
                text="🧪 <b>Mock Mode Active - Test Orders Loaded</b>\n\n"
                     f"Sending {len(mock_orders)} test orders..."
            )

            for order in mock_orders:
                message_text = format_mock_order(order)

                await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    reply_markup=get_order_keyboard(order.order_index)
                )

            logger.info(f"✅ Sent {len(mock_orders)} mock orders to {user['login']}")

        except Exception as e:
            logger.error(f"❌ Failed to send mock orders to {user['login']}: {e}")


def format_mock_order(order) -> str:
    """Format mock order card"""
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
