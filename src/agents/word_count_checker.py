"""
Bot 4: Word Count Checker
Checks if text meets minimum word count requirements
If not enough words, triggers Bot 2 in expand mode
"""
import logging
import re
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.workflows.state import OrderWorkflowState

logger = logging.getLogger(__name__)

MAX_WORD_COUNT_ATTEMPTS = 50  # Increased to allow more iterations


class WordCountChecker(BaseAgent):
    """Agent that verifies text meets word count requirements"""

    def __init__(self):
        super().__init__(agent_name="Bot4:WordCount")

    def count_words(self, text: str) -> int:
        """Count words in text, excluding citations"""
        if not text:
            return 0

        # Remove citations like (Author, Year) for accurate count
        text_no_citations = re.sub(r'\([A-Z][a-z]+(?:\s+(?:&|et al\.))?,?\s*\d{4}\)', '', text)

        return len(text_no_citations.split())

    def calculate_max_words(self, target_words: int, pages_required: int) -> int:
        """
        Calculate maximum allowed words based on page count
        - For 1-4 pages: target + 40%
        - For 5+ pages: target + 10%
        """
        if pages_required <= 4:
            return int(target_words * 1.40)
        else:
            return int(target_words * 1.10)

    def print_status(self, word_count: int, target_words: int, max_words: int, attempts: int):
        """Print formatted word count status"""
        print("\n" + "="*80)
        print("📊 Bot 4: WORD COUNT CHECK")
        print("="*80 + "\n")
        print(f"   Current words: {word_count}")
        print(f"   Target words:  {target_words}")
        print(f"   Maximum words: {max_words}")
        print(f"   Attempts:      {attempts}/{MAX_WORD_COUNT_ATTEMPTS}")

    async def execute(self, state: OrderWorkflowState) -> Dict[str, Any]:
        """
        Check if text meets word count requirements

        Args:
            state: Current workflow state

        Returns:
            Updated state with word_count_ok flag
        """
        self.log_start(state['order_id'])

        # Get text and parameters
        text = state.get('text_with_citations', state.get('draft_text', ''))
        target_words = state.get('target_word_count', 300)
        attempts = state.get('word_count_attempts', 0)

        if not text:
            logger.error("No text to check")
            return self.update_state(
                state,
                status="failed",
                error="No text for word count check"
            )

        # Count words and calculate limits
        word_count = self.count_words(text)
        requirements = state.get('requirements', {})
        pages_required = requirements.get('pages', state.get('pages_required', 1))
        max_words = self.calculate_max_words(target_words, pages_required)

        # Print status
        self.print_status(word_count, target_words, max_words, attempts)

        # Check if text exceeds maximum
        if word_count > max_words:
            print(f"\n   ❌ EXCEEDS MAXIMUM - {word_count - max_words} words over limit")
            print(f"   → Triggering text reduction...")
            print()

            logger.warning(f"Word count too high: {word_count}/{max_words} max")

            # Check if this is after humanization
            post_humanization = state.get("post_humanization_check", False)
            shorten_mode = "shorten_humanized" if post_humanization else "shorten"

            return self.update_state(
                state,
                status="word_count_shortening",
                word_count=word_count,
                word_count_ok=False,
                writer_mode=shorten_mode
            )

        # Check if text meets minimum
        if word_count >= target_words:
            print(f"\n   ✅ PASSED - Word count meets requirements")
            print()

            logger.info(f"Word count OK: {word_count}/{target_words}")

            return self.update_state(
                state,
                status="word_count_ok",
                word_count=word_count,
                word_count_ok=True
            )

        # Text is below target
        words_needed = target_words - word_count
        print(f"\n   ⚠️ BELOW TARGET - Need {words_needed} more words")

        # Check if max attempts reached
        if attempts >= MAX_WORD_COUNT_ATTEMPTS:
            print(f"   ⚠️ Max attempts reached, proceeding anyway")
            print()

            logger.warning(f"Max word count attempts reached: {word_count}/{target_words}")

            return self.update_state(
                state,
                status="word_count_ok",  # Proceed anyway
                word_count=word_count,
                word_count_ok=False
            )

        # Trigger expansion
        print(f"   → Triggering text expansion...")
        print()

        logger.info(f"Word count low: {word_count}/{target_words}, triggering expansion")

        return self.update_state(
            state,
            status="word_count_expanding",
            word_count=word_count,
            word_count_ok=False,
            writer_mode="expand"
        )


# Node function for LangGraph workflow
async def check_word_count_node(state: OrderWorkflowState) -> dict:
    """
    Bot 4: Checks if text meets word count requirements

    Args:
        state: Current workflow state

    Returns:
        Updated state with word_count_ok flag
    """
    checker = WordCountChecker()
    return await checker.execute(state)
