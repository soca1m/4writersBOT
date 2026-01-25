"""
API Service Layer - Single Responsibility Principle
Handles all API interactions with proper abstraction
"""
import logging
from typing import List, Optional
from py4writers import Order
from src.config import USE_MOCK_API

logger = logging.getLogger(__name__)


class APIService:
    """
    Service for API operations following SOLID principles

    Single Responsibility: Manages API connections and data fetching
    Open/Closed: Can be extended with new methods without modification
    Liskov Substitution: Works with any API implementation (Real/Mock)
    Interface Segregation: Only exposes needed methods
    Dependency Inversion: Depends on abstraction (API interface)
    """

    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self._api = None
        self._api_class = self._get_api_class()

    def _get_api_class(self):
        """Get appropriate API class based on config"""
        if USE_MOCK_API:
            from src.utils.mock_api import MockAPI
            return MockAPI
        else:
            from py4writers import API
            return API

    async def __aenter__(self):
        """Async context manager entry"""
        self._api = self._api_class(login=self.login, password=self.password)
        await self._api.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._api:
            await self._api.close()

    async def get_available_orders(self) -> Optional[List[Order]]:
        """Get available orders"""
        try:
            return await self._api.get_orders()
        except Exception as e:
            logger.error(f"Error fetching available orders: {e}")
            return None

    async def get_processing_orders(self) -> Optional[List[Order]]:
        """Get orders currently in processing"""
        try:
            return await self._api.get_processing_orders()
        except Exception as e:
            logger.error(f"Error fetching processing orders: {e}")
            return None

    async def get_completed_orders(self) -> Optional[List[Order]]:
        """Get completed orders"""
        try:
            return await self._api.get_completed_orders()
        except Exception as e:
            logger.error(f"Error fetching completed orders: {e}")
            return None

    async def get_late_orders(self) -> Optional[List[Order]]:
        """Get late orders"""
        try:
            return await self._api.get_late_orders()
        except Exception as e:
            logger.error(f"Error fetching late orders: {e}")
            return None

    async def get_revision_orders(self) -> Optional[List[Order]]:
        """Get revision orders"""
        try:
            return await self._api.get_revision_orders()
        except Exception as e:
            logger.error(f"Error fetching revision orders: {e}")
            return None

    async def take_order(self, order_index: int) -> bool:
        """Take an order"""
        try:
            return await self._api.take_order(order_index)
        except Exception as e:
            logger.error(f"Error taking order {order_index}: {e}")
            return False

    async def get_order_details(self, order_index: int) -> Optional[str]:
        """Get order description"""
        try:
            return await self._api.fetch_order_details(order_index)
        except Exception as e:
            logger.error(f"Error fetching order details: {e}")
            return None

    async def get_order_files(self, order_index: int) -> Optional[List]:
        """Get order files"""
        try:
            return await self._api.get_order_files(order_index)
        except Exception as e:
            logger.error(f"Error fetching order files: {e}")
            return None


def create_api_service(login: str, password: str) -> APIService:
    """
    Factory function for creating API service
    Dependency Injection pattern
    """
    return APIService(login, password)
