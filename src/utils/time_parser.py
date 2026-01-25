"""
Utility for parsing time strings from 4writers platform
"""
import re
from datetime import datetime, timedelta
from typing import Optional


def parse_remaining_time(remaining: str) -> Optional[datetime]:
    """
    Parse 'Time remaining: 0d 19h 4m' format to datetime

    Args:
        remaining: Time remaining string from order

    Returns:
        datetime object representing deadline, or None if parsing fails
    """
    match = re.search(r'(\d+)d\s+(\d+)h\s+(\d+)m', remaining)
    if not match:
        return None

    days, hours, minutes = map(int, match.groups())
    deadline = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)

    return deadline


def format_deadline(deadline: datetime) -> str:
    """
    Format deadline datetime to readable string

    Args:
        deadline: datetime object

    Returns:
        Formatted string like "2026-01-24 20:10"
    """
    return deadline.strftime("%Y-%m-%d %H:%M")
