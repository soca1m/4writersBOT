# Хранилище пользователей
users = [
    {"login": "socalm", "password": "milavalerasocalm", "id": 538700366}
]


def get_users():
    """Возвращает список пользователей"""
    return users


def get_user_by_chat_id(chat_id: int) -> dict:
    """Возвращает пользователя по chat_id"""
    return next((user for user in users if user["id"] == chat_id), None)
