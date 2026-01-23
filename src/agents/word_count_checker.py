"""
Bot 4: Word Count Checker
Checks if text meets minimum word count requirements
If not enough words, triggers Bot 2 in expand mode
"""
import logging
import re

from src.workflows.state import OrderWorkflowState

logger = logging.getLogger(__name__)

MAX_WORD_COUNT_ATTEMPTS = 10


def count_words(text: str) -> int:
    """Count words in text, excluding citations"""
    if not text:
        return 0

    # Remove citations like (Author, Year) for accurate count
    text_no_citations = re.sub(r'\([A-Z][a-z]+(?:\s+(?:&|et al\.))?,?\s*\d{4}\)', '', text)

    return len(text_no_citations.split())


async def check_word_count_node(state: OrderWorkflowState) -> dict:
    """
    Bot 4: Checks if text meets word count requirements

    Args:
        state: Current workflow state

    Returns:
        Updated state with word_count_ok flag
    """
    logger.info(f"📊 Bot 4: Checking word count for order {state['order_id']}...")

    # Use text_with_citations if available, otherwise draft_text
    text = state.get('text_with_citations', state.get('draft_text', ''))
    target_words = state.get('target_word_count', 300)
    attempts = state.get('word_count_attempts', 0)

    if not text:
        logger.error("No text to check")
        return {
            **state,
            "status": "failed",
            "error": "No text for word count check",
            "agent_logs": state.get('agent_logs', []) + ["[Bot4:WordCount] ERROR: No text"]
        }

    word_count = count_words(text)

    print("\n" + "="*80)
    print("📊 Bot 4: WORD COUNT CHECK")
    print("="*80 + "\n")

    print(f"   Current words: {word_count}")
    print(f"   Target words:  {target_words}")
    print(f"   Attempts:      {attempts}/{MAX_WORD_COUNT_ATTEMPTS}")

    # Check if we meet the minimum
    if word_count >= target_words:
        print(f"\n   ✅ PASSED - Word count meets requirements")
        print()

        logger.info(f"Word count OK: {word_count}/{target_words}")

        return {
            **state,
            "word_count": word_count,
            "word_count_ok": True,
            "status": "word_count_ok",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot4:WordCount] OK: {word_count}/{target_words} words"
            ]
        }
    else:
        words_needed = target_words - word_count
        print(f"\n   ⚠️ BELOW TARGET - Need {words_needed} more words")

        # Check if we've exceeded max attempts
        if attempts >= MAX_WORD_COUNT_ATTEMPTS:
            print(f"   ⚠️ Max attempts reached, proceeding anyway")
            print()

            logger.warning(f"Max word count attempts reached: {word_count}/{target_words}")

            return {
                **state,
                "word_count": word_count,
                "word_count_ok": False,
                "status": "word_count_ok",  # Proceed anyway
                "agent_logs": state.get('agent_logs', []) + [
                    f"[Bot4:WordCount] Max attempts: {word_count}/{target_words} words, proceeding"
                ]
            }

        print(f"   → Triggering text expansion...")
        print()

        logger.info(f"Word count low: {word_count}/{target_words}, triggering expansion")

        return {
            **state,
            "word_count": word_count,
            "word_count_ok": False,
            "writer_mode": "expand",  # Set mode for Bot 2
            "status": "word_count_expanding",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot4:WordCount] Low: {word_count}/{target_words}, expanding"
            ]
        }
