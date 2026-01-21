"""
Сервис для работы с LLM (Claude, GPT)
"""
import logging
from typing import Optional
from envparse import env

logger = logging.getLogger(__name__)

# Загружаем переменные окружения
env.read_envfile(".env")


def get_claude_model(model_name: str = "claude-3-5-sonnet-20241022", temperature: float = 0.7):
    """
    Создает и возвращает Claude модель

    Args:
        model_name: Название модели
        temperature: Температура для генерации (0.0-1.0)

    Returns:
        ChatAnthropic модель
    """
    try:
        from langchain_anthropic import ChatAnthropic

        api_key = env.str("ANTHROPIC_API_KEY", default=None)

        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found in .env file")
            return None

        model = ChatAnthropic(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            max_tokens=4096
        )

        logger.info(f"Initialized Claude model: {model_name}")
        return model

    except Exception as e:
        logger.error(f"Error initializing Claude model: {e}")
        return None


def get_openai_model(model_name: str = "gpt-4", temperature: float = 0.7):
    """
    Создает и возвращает OpenAI модель

    Args:
        model_name: Название модели
        temperature: Температура для генерации (0.0-1.0)

    Returns:
        ChatOpenAI модель
    """
    try:
        from langchain_openai import ChatOpenAI

        api_key = env.str("OPENAI_API_KEY", default=None)

        if not api_key:
            logger.error("OPENAI_API_KEY not found in .env file")
            return None

        model = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key
        )

        logger.info(f"Initialized OpenAI model: {model_name}")
        return model

    except Exception as e:
        logger.error(f"Error initializing OpenAI model: {e}")
        return None


def get_fast_model():
    """
    Возвращает быструю и дешевую модель для простых задач

    Returns:
        Быстрая LLM модель (Claude Haiku или GPT-3.5)
    """
    # Пробуем Claude Haiku (быстрый и дешевый)
    model = get_claude_model(model_name="claude-3-haiku-20240307", temperature=0.3)

    if model:
        return model

    # Если нет Claude, пробуем GPT-3.5
    return get_openai_model(model_name="gpt-3.5-turbo", temperature=0.3)


def get_smart_model():
    """
    Возвращает умную модель для сложных задач

    Returns:
        Мощная LLM модель (GPT-4 или Claude Sonnet)
    """
    # Сначала пробуем GPT-4
    model = get_openai_model(model_name="gpt-4o", temperature=0.7)

    if model:
        logger.info("Using GPT-4o for smart tasks")
        return model

    # Если нет GPT, пробуем Claude Sonnet
    model = get_claude_model(model_name="claude-3-5-sonnet-20241022", temperature=0.7)

    if model:
        logger.info("Using Claude Sonnet for smart tasks")
        return model

    logger.error("No smart model available")
    return None
