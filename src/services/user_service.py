"""
User Service - Business Logic Layer
Handles user-related operations
"""
import logging
from typing import Optional, Dict, List

from src.store import get_user_by_chat_id, get_users
from src.db.database import (
    get_user_settings,
    update_user_settings,
    update_criteria,
    toggle_auto_collect,
    get_workflow_stats
)

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user operations
    Single Responsibility: User management
    """

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.user = get_user_by_chat_id(chat_id)

    def is_registered(self) -> bool:
        """Check if user is registered"""
        return self.user is not None

    def get_credentials(self) -> Optional[Dict[str, str]]:
        """Get user credentials"""
        if not self.user:
            return None
        return {
            'login': self.user['login'],
            'password': self.user['password']
        }

    def get_settings(self) -> Dict:
        """Get user settings"""
        return get_user_settings(self.chat_id)

    def update_settings(self, updates: Dict):
        """Update user settings"""
        update_user_settings(self.chat_id, updates)
        logger.info(f"Updated settings for user {self.chat_id}")

    def update_criteria(self, criteria_updates: Dict):
        """Update filter criteria"""
        update_criteria(self.chat_id, criteria_updates)
        logger.info(f"Updated criteria for user {self.chat_id}")

    def toggle_auto_collect(self) -> bool:
        """
        Toggle auto-collection

        Returns:
            New state
        """
        new_state = toggle_auto_collect(self.chat_id)
        logger.info(f"Auto-collect for user {self.chat_id}: {new_state}")
        return new_state

    def get_workflow_stats(self) -> Dict:
        """Get workflow statistics"""
        return get_workflow_stats(self.chat_id)

    @staticmethod
    def get_all_users() -> List[Dict]:
        """Get all registered users"""
        return get_users()


def create_user_service(chat_id: int) -> UserService:
    """
    Factory function for creating user service

    Args:
        chat_id: Telegram chat ID

    Returns:
        UserService instance
    """
    return UserService(chat_id)