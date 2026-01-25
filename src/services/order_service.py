"""
Order Service - Business Logic Layer (Single Responsibility)
Handles all order-related operations
"""
import logging
from typing import List, Optional, Dict
from py4writers import Order

from src.services.api_service import create_api_service
from src.db.database import get_user_settings
from src.store import get_user_by_chat_id

logger = logging.getLogger(__name__)


class OrderService:
    """
    Service for order operations
    Single Responsibility: Order management
    Open/Closed: Can be extended with new order operations
    """

    def __init__(self, user_login: str, user_password: str):
        self.api_service = create_api_service(user_login, user_password)

    async def __aenter__(self):
        """Context manager entry"""
        await self.api_service.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.api_service.__aexit__(exc_type, exc_val, exc_tb)

    async def get_all_orders_by_type(self) -> Dict[str, List[Order]]:
        """
        Get all orders grouped by type

        Returns:
            Dictionary with order types as keys
        """
        return {
            'available': await self.api_service.get_available_orders() or [],
            'processing': await self.api_service.get_processing_orders() or [],
            'completed': await self.api_service.get_completed_orders() or [],
            'late': await self.api_service.get_late_orders() or [],
            'revision': await self.api_service.get_revision_orders() or []
        }

    async def get_order_statistics(self) -> Dict[str, int]:
        """
        Get order counts for statistics

        Returns:
            Dictionary with order counts
        """
        orders = await self.get_all_orders_by_type()

        return {
            'active': len(orders['processing']),
            'completed': len(orders['completed']),
            'late': len(orders['late']),
            'revisions': len(orders['revision'])
        }

    async def take_order(self, order_index: int) -> bool:
        """
        Take an order

        Args:
            order_index: Order index

        Returns:
            Success status
        """
        success = await self.api_service.take_order(order_index)
        if success:
            logger.info(f"Successfully took order {order_index}")
        else:
            logger.warning(f"Failed to take order {order_index}")
        return success

    async def get_order_with_details(self, order_index: int) -> Dict:
        """
        Get order with all details

        Args:
            order_index: Order index

        Returns:
            Dict with order details and files
        """
        details = await self.api_service.get_order_details(order_index)
        files = await self.api_service.get_order_files(order_index)

        return {
            'description': details,
            'files': files or []
        }

    @staticmethod
    def filter_orders_by_criteria(orders: List[Order], criteria: dict) -> List[Order]:
        """
        Filter orders based on user criteria

        Args:
            orders: List of orders
            criteria: Filter criteria

        Returns:
            Filtered orders list
        """
        filtered = orders

        # Price filter
        if criteria.get('min_price'):
            filtered = [o for o in filtered if o.total >= criteria['min_price']]
        if criteria.get('max_price'):
            filtered = [o for o in filtered if o.total <= criteria['max_price']]

        # Pages filter
        if criteria.get('min_pages'):
            filtered = [o for o in filtered if o.pages >= criteria['min_pages']]
        if criteria.get('max_pages'):
            filtered = [o for o in filtered if o.pages <= criteria['max_pages']]

        # Type filter
        if criteria.get('order_types'):
            filtered = [o for o in filtered if o.order_type in criteria['order_types']]

        # Level filter
        if criteria.get('academic_levels'):
            filtered = [o for o in filtered if o.academic_level in criteria['academic_levels']]

        # Subject filter
        if criteria.get('subjects'):
            filtered = [o for o in filtered if o.subject in criteria['subjects']]

        return filtered


def create_order_service(user_login: str, user_password: str) -> OrderService:
    """
    Factory function for creating order service

    Args:
        user_login: User login
        user_password: User password

    Returns:
        OrderService instance
    """
    return OrderService(user_login, user_password)


def create_order_service_for_chat(chat_id: int) -> Optional[OrderService]:
    """
    Factory function for creating order service by chat ID

    Args:
        chat_id: Telegram chat ID

    Returns:
        OrderService instance or None if user not found
    """
    user = get_user_by_chat_id(chat_id)
    if not user:
        return None

    return create_order_service(user["login"], user["password"])