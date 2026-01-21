"""
State модель для LangGraph workflow обработки заказов
"""
from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph.message import add_messages


class OrderWorkflowState(TypedDict):
    """Состояние для workflow обработки заказа"""

    # ===== Исходные данные заказа =====
    order_id: str
    order_index: str  # Для API py4writers
    order_description: str
    pages_required: int
    deadline: str
    attached_files: List[str]  # Список путей к файлам или URLs

    # ===== Извлеченные требования =====
    requirements: Dict[str, any]  # {"type": "discussion_post", "min_words": 600, "sources": 4, etc.}
    parsed_files_content: str  # Содержимое всех прикрепленных файлов

    # ===== Результаты research =====
    sources_found: List[Dict[str, any]]  # [{"title": "...", "url": "...", "year": 2023, "content": "..."}]
    quotes: List[Dict[str, any]]  # [{"quote": "...", "source_id": 0, "relevance": "..."}]

    # ===== Написанный текст =====
    draft_text: str
    word_count: int

    # ===== Проверки качества =====
    meets_requirements: bool
    quality_issues: List[str]  # Список проблем, если есть

    # ===== Плагиат =====
    plagiarism_score: float  # 0-100%
    plagiarism_details: Dict[str, any]
    rewrite_attempts: int

    # ===== Финальный результат =====
    final_text: str
    references: str  # References section отдельно
    status: str  # "analyzing", "researching", "writing", "checking", "rewriting", "done", "rejected", "failed"

    # ===== Логи и сообщения (для отладки и истории) =====
    agent_logs: List[str]  # Простые текстовые логи от агентов
    error: Optional[str]  # Ошибка, если что-то пошло не так
