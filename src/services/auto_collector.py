"""
Auto-collection service for orders based on user criteria
"""
import logging
import re
from datetime import datetime
from typing import List, Optional
from py4writers import Order

from src.db.database import get_user_settings
from src.utils.time_parser import parse_remaining_time

logger = logging.getLogger(__name__)


def parse_deadline_hours(remaining: str) -> Optional[int]:
    """
    Parse remaining time to hours

    Args:
        remaining: Time remaining string (e.g. "Time remaining: 0d 19h 4m")

    Returns:
        Total hours remaining, or None if parsing fails
    """
    match = re.search(r'(\d+)d\s+(\d+)h\s+(\d+)m', remaining)
    if not match:
        return None

    days, hours, minutes = map(int, match.groups())
    total_hours = days * 24 + hours + (minutes / 60)

    return int(total_hours)


def matches_criteria(order: Order, criteria: dict) -> bool:
    """
    Check if order matches user criteria

    Args:
        order: Order object
        criteria: User criteria dict

    Returns:
        True if order matches all criteria
    """
    # Price range
    if criteria.get("min_price") is not None:
        if order.total < criteria["min_price"]:
            logger.debug(f"Order {order.order_id} rejected: price ${order.total} < min ${criteria['min_price']}")
            return False

    if criteria.get("max_price") is not None:
        if order.total > criteria["max_price"]:
            logger.debug(f"Order {order.order_id} rejected: price ${order.total} > max ${criteria['max_price']}")
            return False

    # Pages range
    if criteria.get("min_pages") is not None:
        if order.pages < criteria["min_pages"]:
            logger.debug(f"Order {order.order_id} rejected: pages {order.pages} < min {criteria['min_pages']}")
            return False

    if criteria.get("max_pages") is not None:
        if order.pages > criteria["max_pages"]:
            logger.debug(f"Order {order.order_id} rejected: pages {order.pages} > max {criteria['max_pages']}")
            return False

    # Order types
    if criteria.get("order_types"):
        if order.order_type not in criteria["order_types"]:
            logger.debug(f"Order {order.order_id} rejected: type '{order.order_type}' not in {criteria['order_types']}")
            return False

    # Academic levels
    if criteria.get("academic_levels"):
        if order.academic_level not in criteria["academic_levels"]:
            logger.debug(f"Order {order.order_id} rejected: level '{order.academic_level}' not in {criteria['academic_levels']}")
            return False

    # Subjects
    if criteria.get("subjects"):
        if order.subject not in criteria["subjects"]:
            logger.debug(f"Order {order.order_id} rejected: subject '{order.subject}' not in {criteria['subjects']}")
            return False

    # Minimum deadline
    if criteria.get("min_deadline_hours") is not None:
        deadline_hours = parse_deadline_hours(order.remaining)
        if deadline_hours is not None:
            if deadline_hours < criteria["min_deadline_hours"]:
                logger.debug(f"Order {order.order_id} rejected: deadline {deadline_hours}h < min {criteria['min_deadline_hours']}h")
                return False

    logger.info(f"✅ Order {order.order_id} matches all criteria")
    return True


async def auto_collect_orders(api, chat_id: int) -> List[Order]:
    """
    Auto-collect orders based on user criteria

    Args:
        api: Authenticated API instance
        chat_id: User chat ID

    Returns:
        List of collected orders
    """
    settings = get_user_settings(chat_id)

    # Check if auto-collect is enabled
    if not settings.get("auto_collect_enabled"):
        return []

    max_orders = settings.get("max_orders", 4)
    criteria = settings.get("criteria", {})

    try:
        # Get current processing orders count
        processing_orders = await api.get_processing_orders()
        current_count = len(processing_orders) if processing_orders else 0

        # logger.info(f"User has {current_count}/{max_orders} orders in processing")

        # Check if we can take more orders
        if current_count >= max_orders:
            logger.info(f"Max orders limit ({max_orders}) reached, skipping auto-collection")
            return []

        # Get available orders
        available_orders = await api.get_orders()

        if not available_orders:
            logger.debug("No available orders")
            return []

        collected = []
        slots_available = max_orders - current_count

        logger.info(f"Checking {len(available_orders)} available orders against criteria")

        for order in available_orders:
            if len(collected) >= slots_available:
                logger.info(f"Reached slots limit ({slots_available}), stopping auto-collection")
                break

            # Check if order matches criteria
            if matches_criteria(order, criteria):
                logger.info(f"🎯 Taking order {order.order_id} (#{order.order_index})")

                # Try to take the order
                success = await api.take_order(order.order_index)

                if success:
                    logger.info(f"✅ Successfully took order {order.order_id}")
                    collected.append(order)
                else:
                    logger.warning(f"❌ Failed to take order {order.order_id} (may be already taken)")

        if collected:
            logger.info(f"Auto-collected {len(collected)} orders")
        else:
            logger.debug("No orders matched criteria")

        return collected

    except Exception as e:
        logger.error(f"Error in auto-collection: {e}")
        return []
