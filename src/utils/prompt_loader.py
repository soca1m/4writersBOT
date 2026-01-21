"""
Утилита для загрузки промптов из файлов
Следует принципам SOLID: Single Responsibility, Interface Segregation
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

# Константы для путей к промптам
PROMPTS_DIR: Path = Path(__file__).parent.parent.parent / "prompts"


class PromptType(Enum):
    """Перечисление типов промптов"""
    ANALYZER = "analyzer_prompt"
    REQUIREMENTS_EXTRACTOR = "requirements_extractor_prompt"
    WRITER = "writer_prompt"
    RESEARCHER = "researcher_prompt"
    QUALITY_CHECKER = "quality_checker_prompt"
    PLAGIARISM_CHECKER = "plagiarism_checker_prompt"
    REWRITER = "rewriter_prompt"


class PromptLoadError(Exception):
    """Исключение при ошибке загрузки промпта"""
    pass


class PromptLoader:
    """
    Загрузчик промптов из файловой системы
    Реализует Single Responsibility Principle
    """

    def __init__(self, prompts_directory: Path = PROMPTS_DIR) -> None:
        """
        Инициализация загрузчика промптов

        Args:
            prompts_directory: Директория с файлами промптов
        """
        self.prompts_dir: Path = prompts_directory

    def load_prompt(
        self,
        prompt_type: PromptType,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Загружает промпт из файла и заполняет переменные

        Args:
            prompt_type: Тип промпта из перечисления PromptType
            variables: Словарь переменных для подстановки в промпт

        Returns:
            Заполненный промпт

        Raises:
            PromptLoadError: Если файл не найден или ошибка форматирования
        """
        prompt_file: Path = self.prompts_dir / f"{prompt_type.value}.txt"

        if not prompt_file.exists():
            error_msg: str = f"Prompt file not found: {prompt_file}"
            logger.error(error_msg)
            raise PromptLoadError(error_msg)

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template: str = f.read()

            # Заполняем переменные если они предоставлены
            if variables:
                prompt: str = prompt_template.format(**variables)
            else:
                prompt: str = prompt_template

            logger.info(f"Successfully loaded prompt: {prompt_type.value}")
            return prompt

        except KeyError as e:
            error_msg: str = f"Missing variable in prompt {prompt_type.value}: {e}"
            logger.error(error_msg)
            raise PromptLoadError(error_msg) from e

        except Exception as e:
            error_msg: str = f"Error loading prompt {prompt_type.value}: {e}"
            logger.error(error_msg)
            raise PromptLoadError(error_msg) from e


# Singleton instance для удобства использования
_prompt_loader_instance: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """
    Возвращает singleton instance PromptLoader
    Реализует Dependency Inversion Principle

    Returns:
        Экземпляр PromptLoader
    """
    global _prompt_loader_instance
    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()
    return _prompt_loader_instance


# ========== Фабричные функции для каждого типа промпта ==========
# Реализуют Interface Segregation Principle


def get_analyzer_prompt(
    order_description: str,
    pages_required: int,
    deadline: str
) -> str:
    """
    Возвращает промпт для Analyzer агента

    Args:
        order_description: Описание заказа
        pages_required: Количество страниц
        deadline: Дедлайн

    Returns:
        Промпт для анализа заказа
    """
    loader: PromptLoader = get_prompt_loader()

    variables: Dict[str, Any] = {
        "order_description": order_description[:500],  # Ограничиваем длину
        "pages_required": pages_required,
        "deadline": deadline
    }

    return loader.load_prompt(PromptType.ANALYZER, variables)


def get_requirements_extractor_prompt(
    order_description: str,
    pages_required: int,
    files_content: str
) -> str:
    """
    Возвращает промпт для Requirements Extractor агента

    Args:
        order_description: Описание заказа
        pages_required: Количество страниц
        files_content: Содержимое прикрепленных файлов

    Returns:
        Промпт для извлечения требований
    """
    loader: PromptLoader = get_prompt_loader()

    variables: Dict[str, Any] = {
        "order_description": order_description,
        "pages_required": pages_required,
        "files_content": files_content if files_content else "No files attached"
    }

    return loader.load_prompt(PromptType.REQUIREMENTS_EXTRACTOR, variables)


def get_writer_prompt(
    assignment_type: str,
    main_topic: str,
    target_word_count: int,
    required_sources: int,
    main_question: str,
    files_content: str = "",
    specific_instructions: str = ""
) -> str:
    """
    Возвращает промпт для Writer агента

    Args:
        assignment_type: Тип задания (essay, discussion post, etc.)
        main_topic: Основная тема
        target_word_count: Целевое количество слов
        required_sources: Необходимое количество источников
        main_question: Главный вопрос для ответа
        files_content: Содержимое прикрепленных файлов
        specific_instructions: Дополнительные специфические инструкции

    Returns:
        Промпт для написания текста
    """
    loader: PromptLoader = get_prompt_loader()

    variables: Dict[str, Any] = {
        "assignment_type": assignment_type,
        "main_topic": main_topic,
        "target_word_count": target_word_count,
        "required_sources": required_sources,
        "main_question": main_question,
        "files_content": files_content if files_content else "No additional files provided.",
        "specific_instructions": specific_instructions if specific_instructions else "None"
    }

    return loader.load_prompt(PromptType.WRITER, variables)


def get_researcher_prompt(
    main_topic: str,
    required_sources: int,
    min_year: int = 2020
) -> str:
    """
    Возвращает промпт для Researcher агента

    Args:
        main_topic: Тема для исследования
        required_sources: Количество необходимых источников
        min_year: Минимальный год публикации источников

    Returns:
        Промпт для поиска источников
    """
    loader: PromptLoader = get_prompt_loader()

    variables: Dict[str, Any] = {
        "main_topic": main_topic,
        "required_sources": required_sources,
        "min_year": min_year
    }

    return loader.load_prompt(PromptType.RESEARCHER, variables)


def get_rewriter_prompt(
    current_text: str,
    ai_percentage: float,
    target_word_count: int
) -> str:
    """
    Возвращает промпт для Rewriter агента

    Args:
        current_text: Текущий текст который нужно переписать
        ai_percentage: Процент AI-generated content
        target_word_count: Целевое количество слов

    Returns:
        Промпт для переписывания текста
    """
    loader: PromptLoader = get_prompt_loader()

    variables: Dict[str, Any] = {
        "current_text": current_text,
        "ai_percentage": ai_percentage,
        "target_word_count": target_word_count
    }

    return loader.load_prompt(PromptType.REWRITER, variables)
