"""
Mock API for testing without real API calls
Set USE_MOCK_API=true in .env to enable
"""
import logging
from typing import List, Optional
from py4writers import Order
from src.utils.mock_data import (
    get_mock_orders,
    get_mock_processing_orders,
    get_mock_completed_orders,
    get_mock_late_orders,
    get_mock_revision_orders
)

logger = logging.getLogger(__name__)


class MockAPI:
    """Mock API that returns fake data for testing"""

    def __init__(self, login: str, password: str):
        self.user_login = login
        self.user_password = password
        self.authenticated = False
        logger.info(f"MockAPI initialized for {login}")

    async def login(self):
        """Mock login"""
        self.authenticated = True
        logger.info(f"MockAPI: User {self.user_login} logged in (mock)")

    async def close(self):
        """Mock close"""
        logger.debug("MockAPI: Connection closed (mock)")

    async def get_orders(self) -> Optional[List[Order]]:
        """Get mock available orders"""
        logger.info("MockAPI: Fetching available orders")
        return get_mock_orders()

    async def get_processing_orders(self) -> Optional[List[Order]]:
        """Get mock processing orders"""
        logger.info("MockAPI: Fetching processing orders")
        return get_mock_processing_orders()

    async def get_completed_orders(self) -> Optional[List[Order]]:
        """Get mock completed orders"""
        logger.info("MockAPI: Fetching completed orders")
        return get_mock_completed_orders()

    async def get_late_orders(self) -> Optional[List[Order]]:
        """Get mock late orders"""
        logger.info("MockAPI: Fetching late orders")
        return get_mock_late_orders()

    async def get_revision_orders(self) -> Optional[List[Order]]:
        """Get mock revision orders"""
        logger.info("MockAPI: Fetching revision orders")
        return get_mock_revision_orders()

    async def take_order(self, order_index: int) -> bool:
        """Mock take order"""
        logger.info(f"MockAPI: Taking order {order_index} (mock)")
        return True

    async def fetch_order_details(self, order_index: int) -> Optional[str]:
        """Mock fetch order details"""
        logger.info(f"MockAPI: Fetching details for order {order_index}")
        return (
            "This is a mock order description.\n\n"
            "Requirements:\n"
            "- Use APA style\n"
            "- Minimum 3 pages\n"
            "- Include 5 peer-reviewed sources\n"
            "- Focus on recent studies (2020-2024)\n\n"
            "Please ensure proper citations and formatting."
        )

    async def get_order_files(self, order_index: int) -> Optional[List]:
        """Mock get order files"""
        logger.info(f"MockAPI: Fetching files for order {order_index}")
        return []  # No files for mock

    async def __aenter__(self):
        """Async context manager entry"""
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
