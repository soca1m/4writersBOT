"""
State модель для LangGraph workflow обработки заказов
Новая архитектура: 7 ботов с четким разделением ответственности
"""
from typing import TypedDict, List, Dict, Optional, Literal


class OrderWorkflowState(TypedDict):
    """Состояние для workflow обработки заказа"""

    # ===== Исходные данные заказа =====
    order_id: str
    order_index: str  # Для API py4writers
    order_description: str
    pages_required: int
    deadline: str
    attached_files: List[str]  # Список путей к файлам

    # ===== Bot 1: Requirements Analyzer =====
    requirements: Dict[str, any]  # JSON от LLM с полями:
    # {
    #   "is_sufficient": bool,
    #   "missing_info": str | None,
    #   "assignment_type": str,
    #   "main_topic": str,
    #   "main_question": str,
    #   "required_sources": int,
    #   "search_keywords": str,
    #   "citation_style": str,  # "APA", "MLA", "Harvard"
    #   "structure": {
    #       "introduction_words": int,
    #       "body_sections": [{"heading": str, "words": int}],
    #       "conclusion_words": int
    #   },
    #   "key_points": List[str],
    #   "specific_instructions": str,
    #   "target_word_count": int
    # }
    parsed_files_content: str  # Содержимое всех прикрепленных файлов

    # ===== Bot 2: Writer =====
    # Режимы: "initial", "expand", "revise", "fix_humanized"
    writer_mode: Literal["initial", "expand", "revise", "fix_humanized"]
    draft_text: str  # Текст БЕЗ цитат (raw text)
    text_with_citations: str  # Текст С цитатами (после Bot 3)
    text_before_humanization: str  # Текст ДО humanization (для reference при fix_humanized)

    # ===== Bot 3: Citation Integrator =====
    sources_found: List[Dict[str, any]]  # Список найденных источников
    # [{"title": str, "authors": str, "year": int, "citation": str, "abstract": str, "url": str}]
    citations_inserted: bool  # Были ли вставлены цитаты

    # ===== Bot 4: Word Count Checker =====
    word_count: int
    target_word_count: int
    word_count_ok: bool
    word_count_attempts: int  # Попытки расширения текста (max 10)

    # ===== Bot 5: Quality Checker =====
    quality_ok: bool
    quality_issues: List[str]  # Найденные проблемы
    quality_suggestions: List[str]  # Рекомендации
    citation_action: Literal["keep", "adjust", "reinsert"]  # Что делать с цитатами
    # "keep" - цитаты корректны, не менять
    # "adjust" - цитаты в неправильных позициях (начало/конец параграфа), переставить
    # "reinsert" - источники нерелевантны, найти новые
    quality_check_attempts: int  # Попытки исправления (max 10)

    # ===== Bot 6: AI Detector + Humanizer =====
    ai_score: float  # 0-100% AI detected
    ai_sentences: List[str]  # Предложения с высоким AI score
    ai_check_attempts: int  # Попытки humanize (max 5)
    ai_check_passed: bool
    humanization_mode: Literal["none", "full", "sentence"]  # Режим humanization
    # "none" - не требуется
    # "full" - полная перефразировка (AI > 70%)
    # "sentence" - выборочная по предложениям (5% < AI ≤ 70%)
    humanized_document_id: Optional[str]  # ID документа после humanization
    post_humanization_check: bool  # Прошла ли проверка качества после humanization

    # ===== Bot 7: References Generator =====
    references: str  # APA References section

    # ===== Финальный результат =====
    final_text: str  # Полный текст с цитатами и references
    status: str  # Текущий статус workflow
    # Статусы:
    # "started", "requirements_extracted", "insufficient_info",
    # "text_written", "citations_added", "word_count_ok", "word_count_expanding",
    # "quality_ok", "quality_revising", "ai_passed", "ai_humanizing",
    # "completed", "failed"

    # ===== Логи и ошибки =====
    agent_logs: List[str]
    error: Optional[str]
