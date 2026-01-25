"""
Order Monitor Service - Refactored with Clean Architecture
Monitors orders and sends notifications
"""
import asyncio
import logging
from typing import Dict, List, Set
from aiogram import Bot

from src.services.order_service import create_order_service
from src.services.user_service import UserService
from src.formatters.message_formatters import OrderFormatter
from src.keyboards.order import get_order_keyboard, get_active_order_keyboard
from src.services.auto_collector import auto_collect_orders

logger = logging.getLogger(__name__)

# State storage
previous_orders: Dict[str, Set[str]] = {}  # {user_login: {order_ids}}
previous_active_orders: Dict[str, Set[str]] = {}
order_messages_cache: Dict[int, Dict[int, str]] = {}  # {chat_id: {order_index: message}}


class OrderMonitor:
    """
    Service for monitoring orders
    Single Responsibility: Monitor and notify about order changes
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    async def monitor_user_orders(self, user: dict):
        """
        Monitor orders for a single user

        Args:
            user: User dict with login, password, id
        """
        user_login = user["login"]
        chat_id = user["id"]

        try:
            async with create_order_service(user["login"], user["password"]) as service:
                # Auto-collect orders if enabled
                user_service = UserService(chat_id)
                settings = user_service.get_settings()

                if settings['auto_collect_enabled']:
                    collected = await auto_collect_orders(
                        service.api_service._api,
                        chat_id
                    )

                    for order in collected:
                        await self.send_order_notification(
                            chat_id,
                            order,
                            "🤖 Auto-Collected Order!"
                        )

                # Get all orders
                orders = await service.get_all_orders_by_type()

                # Monitor available orders
                await self.monitor_available_orders(
                    user_login, chat_id, orders['available']
                )

                # Monitor active orders
                await self.monitor_active_orders(
                    user_login, chat_id, orders['processing']
                )

        except Exception as e:
            logger.error(f"Error monitoring orders for {user_login}: {e}")

    async def monitor_available_orders(
        self,
        user_login: str,
        chat_id: int,
        current_orders: List
    ):
        """Monitor changes in available orders"""
        # Get current order IDs
        current_ids = {order.order_id for order in current_orders if order}

        # Get previous order IDs
        previous_ids = previous_orders.get(user_login, set())

        # Find new and removed orders
        new_ids = current_ids - previous_ids
        removed_ids = previous_ids - current_ids

        # Send notifications for new orders
        for order in current_orders:
            if order and order.order_id in new_ids:
                await self.send_order_notification(
                    chat_id,
                    order,
                    "🔔 Новый заказ!"
                )

        # Send notifications for removed orders
        for order_id in removed_ids:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Заказ {order_id} больше недоступен"
            )

        # Update state
        previous_orders[user_login] = current_ids

    async def monitor_active_orders(
        self,
        user_login: str,
        chat_id: int,
        current_orders: List
    ):
        """Monitor changes in active/processing orders"""
        # Get current order IDs
        current_ids = {order.order_id for order in current_orders if order}

        # Get previous order IDs
        previous_ids = previous_active_orders.get(user_login, set())

        # Find new active orders
        new_ids = current_ids - previous_ids

        # Send notifications for new active orders
        for order in current_orders:
            if order and order.order_id in new_ids:
                await self.send_active_order_notification(
                    chat_id,
                    order
                )

        # Update state
        previous_active_orders[user_login] = current_ids

    async def send_order_notification(self, chat_id: int, order, prefix: str = "🔔"):
        """Send notification about new order"""
        formatter = OrderFormatter()
        message_text = formatter.format_order_card(order, prefix=prefix)

        # Cache message
        if chat_id not in order_messages_cache:
            order_messages_cache[chat_id] = {}
        order_messages_cache[chat_id][order.order_index] = message_text

        # Use order_index if available, fallback to order_id
        order_key = order.order_index if order.order_index is not None else order.order_id

        await self.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=get_order_keyboard(order_key)
        )

    async def send_active_order_notification(self, chat_id: int, order):
        """Send notification about new active order"""
        formatter = OrderFormatter()
        message_text = formatter.format_order_card(order, prefix="🔄")

        # Cache message
        if chat_id not in order_messages_cache:
            order_messages_cache[chat_id] = {}
        order_messages_cache[chat_id][order.order_index] = message_text

        await self.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=get_active_order_keyboard(order.order_index)
        )

    async def run(self):
        """Main monitoring loop"""
        logger.info("🔄 Order monitoring started")

        while True:
            user_service = UserService(0)  # Static method access
            users = user_service.get_all_users()

            for user in users:
                await self.monitor_user_orders(user)
                await asyncio.sleep(1)  # Small delay between users

            await asyncio.sleep(5)  # Main loop delay


async def start_monitoring(bot: Bot):
    """
    Start order monitoring

    Args:
        bot: Telegram bot instance
    """
    monitor = OrderMonitor(bot)
    await monitor.run()