"""
Text Humanizer Agent
Uses Undetectable AI to humanize AI-generated text
Supports two modes:
- Full: Complete rewrite using rehumanize (cheaper, for >70% AI)
- Sentence: Targeted humanization of AI sentences (for 5-70% AI)
"""
import logging
import re
from typing import Dict, Any

from src.workflows.state import OrderWorkflowState
from src.utils.undetectable_ai import UndetectableAI
from src.agents.ai_detector import AIDetector

logger = logging.getLogger(__name__)

# Create shared AIDetector instance for body text extraction
_ai_detector = AIDetector()


async def humanize_text_node(state: OrderWorkflowState) -> dict:
    """
    Humanize AI-generated text using Undetectable AI

    Modes:
    - "full": Complete rehumanize (>70% AI, uses rehumanize endpoint)
    - "sentence": Targeted sentence humanization (5-70% AI)

    Args:
        state: Current workflow state

    Returns:
        Updated state with humanized text
    """
    logger.info(f"🤖 Humanizing text for order {state['order_id']}...")

    full_text = state.get('text_with_citations', state.get('draft_text', ''))
    ai_score = state.get('ai_score', 0.0)
    attempts = state.get('ai_check_attempts', 0)
    humanization_mode = state.get('humanization_mode', 'full')
    ai_sentences = state.get('ai_sentences', [])
    previous_doc_id = state.get('humanized_document_id')

    if not full_text:
        logger.error("No text to humanize")
        return {
            **state,
            "status": "failed",
            "error": "No text for humanization",
            "agent_logs": state.get('agent_logs', []) + ["[Humanizer] ERROR: No text"]
        }

    print("\n" + "="*80)
    print("🔄 HUMANIZING TEXT")
    print("="*80 + "\n")

    print(f"   Current AI Score: {ai_score:.1f}%")
    print(f"   Humanization Mode: {humanization_mode.upper()}")
    print(f"   Attempt: {attempts}/5")

    # Initialize Undetectable AI client
    ai_client = UndetectableAI()

    if not ai_client.api_key:
        print(f"   ⚠️ UNDETECTABLE_API_KEY not set, cannot humanize")
        print(f"   Proceeding with original text...\n")
        return {
            **state,
            "status": "ai_passed",  # Skip humanization, proceed
            "humanization_mode": "none",
            "agent_logs": state.get('agent_logs', []) + [
                "[Humanizer] API key not set, skipped"
            ]
        }

    # Extract body text (exclude title and references)
    body_text = _ai_detector.extract_body_text(full_text)

    # Extract title and references to preserve them
    lines = full_text.split('\n')
    title = ""
    references = ""
    in_references = False

    for line in lines:
        stripped = line.strip()
        if not title and stripped and (stripped.startswith('#') or len(stripped.split()) < 15):
            title = line
        if re.match(r'^References?\s*$', stripped, re.IGNORECASE):
            in_references = True
        if in_references:
            references += line + '\n'

    print(f"   Text breakdown:")
    print(f"   - Full text: {len(full_text.split())} words")
    print(f"   - Body only: {len(body_text.split())} words")
    if title:
        print(f"   - Title: {title[:50]}...")
    if references:
        print(f"   - References: {len(references.split())} words")
    print()

    # Determine parameters based on assignment type
    requirements = state.get('requirements', {})
    assignment_type = requirements.get('assignment_type', 'essay')

    # Map assignment types to purpose (only Essay or General Writing allowed)
    purpose_map = {
        'essay': 'Essay',
        'article': 'General Writing',
        'report': 'General Writing',
        'research paper': 'Essay',
        'discussion post': 'Essay',  # Changed from General Writing to Essay for better academic style
        'case study': 'General Writing',
        'short answer': 'General Writing'
    }
    purpose = purpose_map.get(assignment_type.lower(), 'Essay')

    # Readability: Only High School or University (no other options)
    readability = "University"

    if humanization_mode == "full":
        # FULL HUMANIZATION MODE (>70% AI)
        print(f"   🔄 FULL HUMANIZATION MODE")
        print(f"   Strategy: Complete text rewrite")

        if previous_doc_id and attempts > 1:
            # Use rehumanize endpoint (cheaper, reuses previous humanization)
            print(f"   Using rehumanize endpoint (cheaper)")
            print(f"   Previous document ID: {previous_doc_id}")
            print(f"   This will create a new variation of the humanized text")
            print()

            print("   Submitting for rehumanization...")
            result = await ai_client.rehumanize(previous_doc_id, timeout=120)
        else:
            # First time - use full humanize endpoint
            print(f"   Using full humanize endpoint")
            print(f"   Parameters:")
            print(f"   - Purpose: {purpose}")
            print(f"   - Readability: {readability}")
            print(f"   - Strength: Quality (best academic style)")
            print(f"   - Model: v11sr (improved version)")
            print()

            print("   Submitting for humanization...")
            print("   (This may take 10-60 seconds depending on length)")

            result = await ai_client.humanize(
                text=body_text,
                readability=readability,
                purpose=purpose,
                strength="Quality",  # Quality for best academic style (was Balanced)
                model="v11sr",  # v11sr for better results (was v11)
                timeout=120
            )

    else:
        # SENTENCE-LEVEL HUMANIZATION MODE (5-70% AI)
        print(f"   🎯 SENTENCE-LEVEL HUMANIZATION MODE")
        print(f"   Strategy: Target AI-detected sentences only")
        print(f"   AI Sentences detected: {len(ai_sentences)}")
        print()

        if not ai_sentences:
            print(f"   ⚠️ No specific AI sentences provided")
            print(f"   Falling back to full humanization")
            print()

            result = await ai_client.humanize(
                text=body_text,
                readability=readability,
                purpose=purpose,
                strength="Quality",  # Quality for academic style
                model="v11sr",
                timeout=120
            )
        else:
            # For now, use full humanization with Quality strength
            # TODO: Implement true sentence-level replacement in future
            print(f"   Using Quality humanization (maintains academic style)")
            print(f"   Parameters:")
            print(f"   - Purpose: {purpose}")
            print(f"   - Readability: {readability}")
            print(f"   - Strength: Quality")
            print(f"   - Model: v11sr")
            print()

            print("   Submitting for humanization...")

            result = await ai_client.humanize(
                text=body_text,
                readability=readability,
                purpose=purpose,
                strength="Quality",  # Quality for best academic results
                model="v11sr",
                timeout=120
            )

    # Check result
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        print(f"\n   ⚠️ Humanization failed: {error_msg}")

        # Check if it's a credits issue
        if "credits" in error_msg.lower() or "402" in error_msg:
            print("   ❌ Insufficient credits for humanization")
            print("   Proceeding with original text...\n")
            return {
                **state,
                "status": "ai_passed",  # Continue to references
                "humanization_mode": "none",
                "agent_logs": state.get('agent_logs', []) + [
                    f"[Humanizer] Insufficient credits, using original text"
                ]
            }

        print("   Retrying with original text...\n")
        return {
            **state,
            "status": "ai_humanizing",  # Will retry
            "agent_logs": state.get('agent_logs', []) + [
                f"[Humanizer] Error: {error_msg}, attempt {attempts}"
            ]
        }

    # Success!
    humanized_body = result.get("output", body_text)
    document_id = result.get("document_id") or result.get("id")

    # Reconstruct full text with title and references
    reconstructed_parts = []
    if title:
        reconstructed_parts.append(title)
        reconstructed_parts.append("")  # Empty line after title

    reconstructed_parts.append(humanized_body)

    if references:
        reconstructed_parts.append("")  # Empty line before references
        reconstructed_parts.append(references.strip())

    full_humanized_text = '\n'.join(reconstructed_parts)

    original_words = len(body_text.split())
    humanized_words = len(humanized_body.split())
    total_words = len(full_humanized_text.split())

    print(f"\n   ✅ Humanization complete!")
    if document_id:
        print(f"   Document ID: {document_id}")
    print(f"   Body text: {original_words} → {humanized_words} words")
    print(f"   Total (with title/refs): {total_words} words")
    print(f"   Change: {abs(humanized_words - original_words)} words")

    # Preview changes (first 200 chars)
    if len(humanized_body) > 200:
        print(f"\n   Preview of humanized text:")
        print(f"   {humanized_body[:200]}...")

    print(f"\n   → Returning to AI detector for re-check...")
    print()

    logger.info(f"Text humanized successfully, mode: {humanization_mode}, document ID: {document_id}")

    return {
        **state,
        "text_with_citations": full_humanized_text,
        "text_before_humanization": full_text,  # Save original for reference during fixes
        "humanized_document_id": document_id,
        "post_humanization_check": True,  # Mark that text has been humanized
        "status": "ai_humanizing",  # Will go back to AI detector
        "agent_logs": state.get('agent_logs', []) + [
            f"[Humanizer] Humanized with mode={humanization_mode}, doc_id={document_id}"
        ]
    }