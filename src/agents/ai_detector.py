"""
Bot 6: AI Detector + Humanizer
Checks text for AI detection using ZeroGPT API
If detected as AI, humanizes flagged sentences
Max 5 attempts
"""
import logging
import os
import re
from typing import Dict, Any, List

import httpx

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_smart_model

logger = logging.getLogger(__name__)

MAX_AI_ATTEMPTS = 5
AI_THRESHOLD = 50.0  # Percentage threshold for AI detection


async def check_zerogpt(text: str) -> Dict[str, Any]:
    """
    Check text using ZeroGPT API

    Args:
        text: Text to check

    Returns:
        Dict with ai_percentage and flagged sentences
    """
    api_key = os.getenv("ZEROGPT_API_KEY")

    if not api_key:
        logger.warning("ZEROGPT_API_KEY not set, skipping AI detection")
        return {"ai_percentage": 0, "sentences": [], "error": "API key not set"}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.zerogpt.com/api/detect/detectText",
                headers={
                    "ApiKey": api_key,
                    "Content-Type": "application/json"
                },
                json={"input_text": text[:10000]}  # API limit
            )

            if response.status_code != 200:
                logger.error(f"ZeroGPT API error: {response.status_code}")
                return {"ai_percentage": 0, "sentences": [], "error": f"API error {response.status_code}"}

            data = response.json()

            if not data.get("success"):
                return {"ai_percentage": 0, "sentences": [], "error": "API returned unsuccessful"}

            result = data.get("data", {})
            ai_percentage = result.get("fakePercentage", 0)
            sentences = result.get("sentences", [])

            # Extract flagged sentences (those marked as AI)
            flagged = []
            for s in sentences:
                if s.get("isAI", False):
                    flagged.append(s.get("text", ""))

            return {
                "ai_percentage": ai_percentage,
                "sentences": flagged,
                "error": None
            }

    except Exception as e:
        logger.error(f"ZeroGPT error: {e}")
        return {"ai_percentage": 0, "sentences": [], "error": str(e)}


async def humanize_text(text: str, flagged_sentences: List[str], llm) -> str:
    """
    Humanize AI-flagged sentences while preserving citations

    Args:
        text: Full text
        flagged_sentences: Sentences flagged as AI-generated
        llm: Language model

    Returns:
        Humanized text
    """
    if not flagged_sentences:
        return text

    # Format flagged sentences for prompt
    flagged_list = "\n".join([f"- {s}" for s in flagged_sentences[:10]])

    prompt = f"""Rewrite ONLY the flagged sentences to sound more human and natural.

FULL TEXT:
{text}

SENTENCES FLAGGED AS AI-GENERATED (rewrite these):
{flagged_list}

HUMANIZATION RULES:
1. ONLY rewrite the flagged sentences
2. Keep the SAME meaning and information
3. PRESERVE all citations exactly as they are: (Author, Year)
4. Use more natural, varied sentence structures
5. Add occasional colloquialisms or personal touches
6. Vary sentence length
7. Keep academic tone but make it sound like a human student wrote it

IMPORTANT:
- Do NOT change non-flagged sentences
- Do NOT remove or modify citations
- Do NOT add new information
- Keep the same overall structure

Return the COMPLETE text with humanized sentences."""

    try:
        response = await llm.ainvoke(prompt)
        return response.content.strip()
    except Exception as e:
        logger.error(f"Humanization error: {e}")
        return text


async def check_ai_detection_node(state: OrderWorkflowState) -> dict:
    """
    Bot 6: Checks for AI detection and humanizes if needed

    Args:
        state: Current workflow state

    Returns:
        Updated state with AI check results
    """
    logger.info(f"🤖 Bot 6: Checking AI detection for order {state['order_id']}...")

    text = state.get('text_with_citations', state.get('draft_text', ''))
    attempts = state.get('ai_check_attempts', 0)

    if not text:
        logger.error("No text to check")
        return {
            **state,
            "status": "failed",
            "error": "No text for AI detection",
            "agent_logs": state.get('agent_logs', []) + ["[Bot6:AIDetector] ERROR: No text"]
        }

    print("\n" + "="*80)
    print("🤖 Bot 6: AI DETECTION CHECK")
    print("="*80 + "\n")

    print(f"   Checking with ZeroGPT...")
    print(f"   Attempts: {attempts}/{MAX_AI_ATTEMPTS}")
    print()

    # Check with ZeroGPT
    result = await check_zerogpt(text)

    if result.get("error"):
        print(f"   ⚠️ ZeroGPT error: {result['error']}")
        print(f"   Proceeding without AI check...\n")
        return {
            **state,
            "ai_score": 0,
            "ai_sentences": [],
            "ai_check_passed": True,
            "status": "ai_passed",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot6:AIDetector] API error, skipped: {result['error']}"
            ]
        }

    ai_percentage = result["ai_percentage"]
    flagged_sentences = result["sentences"]

    print(f"   AI Score: {ai_percentage:.1f}%")
    print(f"   Threshold: {AI_THRESHOLD}%")
    print(f"   Flagged sentences: {len(flagged_sentences)}")

    # Check if passed
    if ai_percentage < AI_THRESHOLD:
        print(f"\n   ✅ AI CHECK PASSED\n")
        logger.info(f"AI check passed: {ai_percentage}%")

        return {
            **state,
            "ai_score": ai_percentage,
            "ai_sentences": flagged_sentences,
            "ai_check_passed": True,
            "status": "ai_passed",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot6:AIDetector] PASSED: {ai_percentage:.1f}%"
            ]
        }

    # AI detected - need to humanize
    print(f"\n   ⚠️ AI DETECTED - Humanizing text...")

    # Check max attempts
    if attempts >= MAX_AI_ATTEMPTS:
        print(f"   ⚠️ Max attempts reached, proceeding anyway\n")
        logger.warning(f"Max AI attempts reached: {ai_percentage}%")

        return {
            **state,
            "ai_score": ai_percentage,
            "ai_sentences": flagged_sentences,
            "ai_check_passed": False,
            "status": "ai_passed",  # Proceed anyway
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot6:AIDetector] Max attempts: {ai_percentage:.1f}%, proceeding"
            ]
        }

    # Humanize the text
    llm = get_smart_model()
    if not llm:
        logger.warning("LLM not available for humanization")
        return {
            **state,
            "ai_score": ai_percentage,
            "ai_sentences": flagged_sentences,
            "ai_check_passed": False,
            "ai_check_attempts": attempts + 1,
            "status": "ai_humanizing",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot6:AIDetector] LLM unavailable for humanization"
            ]
        }

    humanized_text = await humanize_text(text, flagged_sentences, llm)

    print(f"   Text humanized, will recheck...\n")
    logger.info(f"Text humanized, attempt {attempts + 1}")

    return {
        **state,
        "text_with_citations": humanized_text,
        "ai_score": ai_percentage,
        "ai_sentences": flagged_sentences,
        "ai_check_passed": False,
        "ai_check_attempts": attempts + 1,
        "status": "ai_humanizing",
        "agent_logs": state.get('agent_logs', []) + [
            f"[Bot6:AIDetector] Humanized: {ai_percentage:.1f}%, attempt {attempts + 1}"
        ]
    }
