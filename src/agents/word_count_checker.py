"""
Word Count Checker - проверяет количество слов в тексте
"""
import logging
from typing import Dict

from src.workflows.state import OrderWorkflowState
from src.utils.text_analysis import count_words

logger = logging.getLogger(__name__)


async def check_word_count_node(state: OrderWorkflowState) -> dict:
    """
    Проверяет количество слов в сгенерированном тексте

    Формула:
    - target = pages * 300
    - minimum = target (строго не меньше)
    - maximum = target + 100
    - ideal = exactly target

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с результатами проверки
    """
    logger.info(f"🔢 Checking word count for order {state['order_id']}...")

    draft_text: str = state.get('draft_text', '')

    if not draft_text:
        logger.error("No draft text found for word count check")
        return {
            **state,
            "status": "word_count_failed",
            "error": "No text to check",
            "agent_logs": state.get('agent_logs', []) + ["[word_count_checker] ERROR: No text to check"]
        }

    # Подсчитываем слова
    word_count: int = count_words(draft_text)

    # Расчёт целевого количества: pages * 300
    pages: int = state['pages_required']
    target_word_count: int = pages * 300
    minimum_acceptable: int = target_word_count
    maximum_acceptable: int = target_word_count + 100

    logger.info(f"Word count: {word_count}, target: {target_word_count} (acceptable: {minimum_acceptable}-{maximum_acceptable})")

    # Проверяем достаточность
    if word_count < minimum_acceptable:
        words_needed: int = minimum_acceptable - word_count
        logger.warning(f"⚠️  Insufficient word count: {word_count}/{minimum_acceptable} (need +{words_needed} words)")

        return {
            **state,
            "status": "insufficient_words",
            "word_count": word_count,
            "agent_logs": state.get('agent_logs', []) + [
                f"[word_count_checker] INSUFFICIENT: {word_count}/{target_word_count} words (need +{words_needed})"
            ]
        }

    elif word_count > maximum_acceptable:
        words_over: int = word_count - maximum_acceptable
        logger.warning(f"⚠️  Too many words: {word_count}/{maximum_acceptable} (over by {words_over} words)")

        return {
            **state,
            "status": "too_many_words",
            "word_count": word_count,
            "final_text": draft_text,  # Устанавливаем final_text для AI проверки
            "agent_logs": state.get('agent_logs', []) + [
                f"[word_count_checker] TOO MANY: {word_count}/{maximum_acceptable} words (over by {words_over})"
            ]
        }

    else:
        # Количество слов в допустимом диапазоне
        if word_count == target_word_count:
            logger.info(f"✅ Perfect word count: {word_count} words")
            status_msg: str = "PERFECT"
        else:
            logger.info(f"✅ Acceptable word count: {word_count} words (target: {target_word_count})")
            status_msg: str = "ACCEPTABLE"

        return {
            **state,
            "status": "word_count_ok",
            "word_count": word_count,
            "final_text": draft_text,  # Текст готов
            "agent_logs": state.get('agent_logs', []) + [
                f"[word_count_checker] {status_msg}: {word_count}/{target_word_count} words"
            ]
        }
