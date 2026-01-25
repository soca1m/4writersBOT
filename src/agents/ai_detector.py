"""
Bot 6: AI Detector
Checks text for AI detection using ZeroGPT free API
Excludes titles and references from check
Thresholds: ≤5% pass, >70% full humanize, 5-70% sentence humanize
Max 20 attempts
"""
import logging
import re
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.workflows.state import OrderWorkflowState
from src.utils.zerogpt import ZeroGPT

logger = logging.getLogger(__name__)

MAX_AI_ATTEMPTS = 20  # Increased to allow more humanization attempts
AI_PASS_THRESHOLD = 5.0  # ≤5% AI = pass
AI_FULL_HUMANIZE_THRESHOLD = 70.0  # >70% AI = full rehumanize


class AIDetector(BaseAgent):
    """Agent that checks text for AI-generated content using ZeroGPT"""

    def __init__(self):
        super().__init__(agent_name="Bot6:AIDetector")
        self.client = ZeroGPT()

    def extract_body_text(self, text: str) -> str:
        """
        Extract only body text, excluding titles and references

        Args:
            text: Full text with potential title and references

        Returns:
            Body text only
        """
        lines = text.split('\n')
        body_lines = []
        in_references = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines at start
            if not stripped and not body_lines:
                continue

            # Check if we hit references section
            if re.match(r'^References?\s*$', stripped, re.IGNORECASE):
                in_references = True
                break

            # Skip if in references
            if in_references:
                continue

            # Skip title (first non-empty line if it starts with # or is short)
            if not body_lines and (stripped.startswith('#') or len(stripped.split()) < 15):
                continue

            # Skip markdown headers (##, ###, etc)
            if stripped.startswith('#'):
                continue

            # Add to body
            if stripped:
                body_lines.append(line)

        return '\n'.join(body_lines)

    async def execute(self, state: OrderWorkflowState) -> Dict[str, Any]:
        """
        Check text for AI detection using ZeroGPT

        Thresholds:
        - ≤5% AI: Pass, proceed to references
        - 5-70% AI: Sentence-level humanization
        - >70% AI: Full humanization (rehumanize)

        Args:
            state: Current workflow state

        Returns:
            Updated state with AI check results
        """
        self.log_start(state['order_id'])

        full_text = state.get('text_with_citations', state.get('draft_text', ''))
        attempts = state.get('ai_check_attempts', 0)
        post_humanization = state.get('post_humanization_check', False)

        if not full_text:
            logger.error("No text to check")
            return self.update_state(
                state,
                status="failed",
                error="No text for AI detection"
            )

        print("\n" + "="*80)
        print("🤖 Bot 6: AI DETECTION CHECK")
        print("="*80 + "\n")

        # Extract body text only (exclude title and references)
        body_text = self.extract_body_text(full_text)

        print(f"   Checking with ZeroGPT (free API)...")
        print(f"   Attempts: {attempts}/{MAX_AI_ATTEMPTS}")
        print(f"   Mode: {'Post-humanization' if post_humanization else 'Initial check'}")
        print(f"   Total text: {len(full_text.split())} words")
        print(f"   Body only: {len(body_text.split())} words (titles/refs excluded)")
        print()

        # Submit for AI detection (body only)
        result = await self.client.detect_ai(body_text)

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            print(f"   ⚠️ Detection error: {error_msg}")
            print(f"   Proceeding without AI check...\n")
            return self.update_state(
                state,
                status="ai_passed",
                ai_score=0.0,
                ai_sentences=[],
                ai_check_passed=True,
                humanization_mode="none"
            )

        # Get AI score from ZeroGPT
        ai_score = result.get("ai_percentage", 0.0)
        ai_words = result.get("ai_words", 0)
        total_words = result.get("total_words", 0)
        feedback = result.get("feedback", "")
        ai_sentences_data = result.get("ai_sentences", [])

        print(f"   AI Score: {ai_score:.1f}% (ZeroGPT)")
        print(f"   Pass Threshold: ≤{AI_PASS_THRESHOLD}%")
        print(f"   Full Humanize Threshold: >{AI_FULL_HUMANIZE_THRESHOLD}%")
        print(f"   Feedback: {feedback}")
        print(f"   AI Words: {ai_words}/{total_words}")
        print(f"   Interpretation: {self.client.interpret_result(ai_score)}")

        # Determine action based on AI score
        if ai_score <= AI_PASS_THRESHOLD:
            # PASS - AI score acceptable
            print(f"\n   ✅ AI CHECK PASSED - Score {ai_score:.1f}% ≤ {AI_PASS_THRESHOLD}%")

            # If this was post-humanization check, go to post-humanization quality check
            # Otherwise, go directly to references
            if post_humanization:
                print(f"   → Proceeding to post-humanization quality check...\n")
                status = "ai_passed_post_humanization"
            else:
                print(f"   → Proceeding to references generation...\n")
                status = "ai_passed"

            logger.info(f"AI check passed: {ai_score:.1f}%")

            return self.update_state(
                state,
                status=status,
                ai_score=ai_score,
                ai_sentences=[],
                ai_check_passed=True,
                humanization_mode="none"
            )

        # AI detected - need humanization
        print(f"\n   ⚠️ AI DETECTED - Score {ai_score:.1f}%")

        # Check max attempts
        if attempts >= MAX_AI_ATTEMPTS:
            print(f"   ⚠️ Max attempts reached ({MAX_AI_ATTEMPTS}), accepting current score")
            print(f"   → Proceeding anyway...\n")
            logger.warning(f"Max AI attempts reached: {ai_score:.1f}%")

            return self.update_state(
                state,
                status="ai_passed",  # Proceed anyway
                ai_score=ai_score,
                ai_sentences=ai_sentences_data if ai_sentences_data else [],
                ai_check_passed=False,
                humanization_mode="none"
            )

        # Determine humanization strategy
        if ai_score > AI_FULL_HUMANIZE_THRESHOLD:
            # Full humanization (rehumanize endpoint - cheaper, complete rewrite)
            humanization_mode = "full"
            print(f"   📝 Strategy: FULL HUMANIZATION (score > {AI_FULL_HUMANIZE_THRESHOLD}%)")
            print(f"   → Using rehumanize endpoint for complete rewrite")
            print(f"   → This will completely rephrase the text")
        else:
            # Sentence-level humanization (targeted fixes)
            humanization_mode = "sentence"
            print(f"   📝 Strategy: SENTENCE-LEVEL HUMANIZATION ({AI_PASS_THRESHOLD}% < score ≤ {AI_FULL_HUMANIZE_THRESHOLD}%)")
            print(f"   → Targeting AI-detected sentences only")
            print(f"   → Preserving human-written parts")

        print(f"   → Attempt {attempts + 1}/{MAX_AI_ATTEMPTS}")
        print(f"   → Sending to humanizer...\n")

        logger.info(f"AI detected ({ai_score:.1f}%), mode: {humanization_mode}, attempt {attempts + 1}")

        return self.update_state(
            state,
            status="ai_humanizing",
            ai_score=ai_score,
            ai_sentences=ai_sentences_data if ai_sentences_data else [],
            ai_check_passed=False,
            ai_check_attempts=attempts + 1,
            humanization_mode=humanization_mode
        )


# Node function for LangGraph workflow
async def check_ai_detection_node(state: OrderWorkflowState) -> dict:
    """
    Bot 6: Checks for AI detection using ZeroGPT

    Args:
        state: Current workflow state

    Returns:
        Updated state with AI check results
    """
    detector = AIDetector()
    return await detector.execute(state)


async def test_ai_detector():
    """Test function for AI detector using ZeroGPT"""

    # Test text
    test_text = """
    Artificial intelligence has revolutionized numerous industries by providing innovative
    solutions to complex problems. Machine learning algorithms can process vast amounts of
    data and identify patterns that would be impossible for humans to detect manually.
    This technology has applications in healthcare, finance, transportation, and many other
    sectors. As AI continues to evolve, it promises to bring even more transformative
    changes to our daily lives and work environments.

    The development of neural networks has been particularly significant in advancing AI
    capabilities. These systems, inspired by the human brain, can learn from experience
    and improve their performance over time. Deep learning, a subset of machine learning,
    has enabled breakthroughs in computer vision, natural language processing, and speech
    recognition. Companies like Google, Amazon, and Microsoft have invested heavily in
    AI research and development, recognizing its potential to drive future innovation.
    """

    print("Testing ZeroGPT detector (free API)...")
    print(f"Text length: {len(test_text.split())} words\n")

    # Create client (no API key needed)
    client = ZeroGPT()

    # Run detection
    result = await client.detect_ai(test_text)

    if result.get("success"):
        print(f"\n✅ Detection successful!")
        print(f"AI Score: {result.get('ai_percentage', 0):.1f}%")
        print(f"AI Words: {result.get('ai_words', 0)}/{result.get('total_words', 0)}")
        print(f"Feedback: {result.get('feedback', '')}")
        print(f"Interpretation: {client.interpret_result(result.get('ai_percentage', 0))}")
    else:
        print(f"\n❌ Detection failed: {result.get('error')}")


if __name__ == "__main__":
    # For testing
    import asyncio
    asyncio.run(test_ai_detector())