"""
Унифицированный сервис для работы с LLM через OpenRouter
Поддерживает любые модели: Claude, GPT, Gemini и другие
"""
import logging
from typing import Optional
from envparse import env
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Загружаем переменные окружения
env.read_envfile(".env")


class OpenRouterLLM:
    """Универсальный класс для работы с любыми LLM через OpenRouter"""

    def __init__(self):
        """Инициализация OpenRouter клиента"""
        self.api_key = env.str("OPENROUTER_API_KEY", default=None)
        self.base_url = "https://openrouter.ai/api/v1"

        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not found in .env file")
            raise ValueError("OPENROUTER_API_KEY is required")

        logger.info("Initialized OpenRouter LLM service")

    def get_model(
        self,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Создает и возвращает LLM модель через OpenRouter

        Args:
            model_name: Название модели (например: "anthropic/claude-3.5-sonnet")
            temperature: Температура для генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе (None = без ограничений)
            **kwargs: Дополнительные параметры для модели

        Returns:
            ChatOpenAI модель с OpenRouter endpoint
        """
        try:
            # Создаём параметры модели
            model_params = {
                "model": model_name,
                "temperature": temperature,
                "api_key": self.api_key,
                "base_url": self.base_url,
                **kwargs
            }

            # Добавляем max_tokens только если указан
            if max_tokens is not None:
                model_params["max_tokens"] = max_tokens

            model = ChatOpenAI(**model_params)

            logger.info(f"Created model: {model_name} (temp={temperature}, max_tokens={max_tokens or 'unlimited'})")
            return model

        except Exception as e:
            logger.error(f"Error creating model {model_name}: {e}")
            return None


# Singleton instance
_openrouter_llm = None


def get_openrouter_service() -> OpenRouterLLM:
    """Возвращает singleton instance OpenRouterLLM"""
    global _openrouter_llm
    if _openrouter_llm is None:
        _openrouter_llm = OpenRouterLLM()
    return _openrouter_llm


def get_claude_model(
    model_name: str = "anthropic/claude-sonnet-4.5",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
):
    """
    Создает Claude модель через OpenRouter

    Args:
        model_name: Версия Claude (по умолчанию: claude-4.5-sonnet)
        temperature: Температура генерации
        max_tokens: Максимум токенов (None = без ограничений)

    Returns:
        LLM модель
    """
    service = get_openrouter_service()
    return service.get_model(model_name, temperature, max_tokens)


def get_openai_model(
    model_name: str = "openai/gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
):
    """
    Создает OpenAI модель через OpenRouter

    Args:
        model_name: Версия GPT (по умолчанию: gpt-4o-mini)
        temperature: Температура генерации
        max_tokens: Максимум токенов (None = без ограничений)

    Returns:
        LLM модель
    """
    service = get_openrouter_service()
    return service.get_model(model_name, temperature, max_tokens)


def get_fast_model():
    """
    Возвращает быструю и дешевую модель для простых задач (анализ, интеграция цитат)

    Returns:
        Быстрая LLM модель (Claude 4.5 Haiku) без ограничений по токенам
    """
    model_name = env.str("FAST_MODEL", default="anthropic/claude-haiku-4.5")
    logger.info(f"Using fast model: {model_name}")
    return get_claude_model(model_name=model_name, temperature=0.3, max_tokens=None)


def get_smart_model(use_reasoning: bool = False):
    """
    Возвращает умную модель для сложных задач (генерация текста, переписывание)

    Args:
        use_reasoning: Включить extended thinking (reasoning) для модели

    Returns:
        Мощная LLM модель (Claude 4.5 Sonnet) без ограничений по токенам
    """
    model_name = env.str("SMART_MODEL", default="anthropic/claude-sonnet-4.5")
    logger.info(f"Using smart model: {model_name} (reasoning={use_reasoning})")

    if use_reasoning:
        # Add reasoning parameter via model_kwargs
        service = get_openrouter_service()
        return service.get_model(
            model_name=model_name,
            temperature=0.7,
            max_tokens=None,
            model_kwargs={
                "extra_body": {
                    "reasoning": {
                        "max_tokens": 2000
                    }
                }
            }
        )
    else:
        return get_claude_model(model_name=model_name, temperature=0.7, max_tokens=None)


def get_writer_model():
    """
    Возвращает модель для генерации академических текстов

    Returns:
        Writer LLM модель (Claude 4.5 Sonnet) без ограничений по токенам
    """
    model_name = env.str("WRITER_MODEL", default="anthropic/claude-sonnet-4.5")
    logger.info(f"Using writer model: {model_name}")
    return get_claude_model(model_name=model_name, temperature=0.7, max_tokens=None)


def get_analyzer_model():
    """
    Возвращает модель для анализа требований и проверки качества

    Returns:
        Analyzer LLM модель (Claude 4.5 Haiku) без ограничений по токенам
    """
    model_name = env.str("ANALYZER_MODEL", default="anthropic/claude-haiku-4.5")
    logger.info(f"Using analyzer model: {model_name}")
    return get_claude_model(model_name=model_name, temperature=0.3, max_tokens=None)


def get_custom_model(model_name: str, temperature: float = 0.7, max_tokens: Optional[int] = None):
    """
    Создает кастомную модель

    Args:
        model_name: Полное название модели из OpenRouter
        temperature: Температура
        max_tokens: Максимум токенов (None = без ограничений)

    Returns:
        LLM модель
    """
    service = get_openrouter_service()
    return service.get_model(model_name, temperature, max_tokens)


# Список доступных моделей для справки
AVAILABLE_MODELS = {
    # Anthropic Claude
    "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-3-opus": "anthropic/claude-3-opus",
    "claude-3-sonnet": "anthropic/claude-3-sonnet",
    "claude-3-haiku": "anthropic/claude-3-haiku",

    # OpenAI GPT
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",

    # Google Gemini
    "gemini-2.0-flash": "google/gemini-2.0-flash-exp:free",
    "gemini-pro": "google/gemini-pro",

    # Meta Llama
    "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
    "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",

    # Mistral
    "mistral-large": "mistralai/mistral-large",
    "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
}


def list_available_models():
    """Выводит список доступных моделей"""
    print("\n🤖 Доступные модели через OpenRouter:\n")
    for name, full_name in AVAILABLE_MODELS.items():
        print(f"  • {name:20} → {full_name}")
    print()
