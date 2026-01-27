"""
Bot 2: Writer
Пишет текст в трех режимах:
- initial: первоначальное написание
- expand: расширение текста (добавление предложений)
- revise: исправление по замечаниям качества
НЕ вставляет цитаты - это делает Bot 3
"""
import logging
from typing import Dict

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_smart_model
from src.agents.writer_modes import (
    InitialMode, ExpandMode, ShortenMode, ShortenHumanizedMode,
    ReviseMode, FixHumanizedMode, WriterMode
)

logger = logging.getLogger(__name__)


def count_words(text: str) -> int:
    """Подсчитывает количество слов в тексте"""
    if not text:
        return 0
    return len(text.split())


# Mode factory for cleaner mode instantiation
MODE_FACTORY = {
    "initial": InitialMode,
    "expand": ExpandMode,
    "shorten": ShortenMode,
    "shorten_humanized": ShortenHumanizedMode,
    "revise": ReviseMode,
    "fix_humanized": FixHumanizedMode
}


async def write_text_node(state: OrderWorkflowState) -> dict:
    """
    Bot 2: Пишет текст в зависимости от режима

    Режимы:
    - initial: первое написание текста по требованиям
    - expand: добавление предложений для увеличения word count
    - shorten: сокращение текста до максимального лимита
    - shorten_humanized: сокращение humanized текста с сохранением стиля
    - revise: переписывание с учетом quality issues
    - fix_humanized: исправление критических ошибок после гуманизации

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с draft_text
    """
    mode = state.get('writer_mode', 'initial')
    requirements = state.get('requirements', {})

    logger.info(f"✍️ Bot 2: Writing text in '{mode}' mode for order {state['order_id']}...")

    try:
        llm = get_smart_model()

        if not llm:
            logger.error("Smart LLM not available")
            return {
                **state,
                "status": "failed",
                "error": "LLM not available for writing",
                "agent_logs": state.get('agent_logs', []) + ["[Bot2:Writer] ERROR: LLM not available"]
            }

        # Get mode class from factory
        mode_class = MODE_FACTORY.get(mode)

        if not mode_class:
            logger.error(f"Unknown writer mode: {mode}")
            return {
                **state,
                "status": "failed",
                "error": f"Unknown writer mode: {mode}",
                "agent_logs": state.get('agent_logs', []) + [f"[Bot2:Writer] ERROR: Unknown mode {mode}"]
            }

        # Instantiate and execute mode strategy
        mode_instance: WriterMode = mode_class()
        return await mode_instance.execute(state, llm, requirements)

    except Exception as e:
        logger.error(f"Error in writer: {e}")
        logger.exception(e)
        return {
            **state,
            "status": "failed",
            "error": f"Writing failed: {str(e)}",
            "agent_logs": state.get('agent_logs', []) + [f"[Bot2:Writer] ERROR: {str(e)}"]
        }
