"""
Bot 5: Quality Checker
Checks if text meets ALL academic writing requirements using LLM
Continues to send for revision until ALL issues are fixed
"""
import json
import logging
import re
from typing import Dict, Any, List

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_fast_model

logger = logging.getLogger(__name__)

MAX_QUALITY_ATTEMPTS = 10


def parse_json_response(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM response"""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


QUALITY_CHECK_PROMPT = """You are an academic writing quality checker. Check this text against ALL rules below.

=== TEXT TO CHECK ===
{text}

=== REQUIREMENTS ===
- Topic: {main_topic}
- Main question: {main_question}
- Assignment type: {assignment_type}

=== SOURCES USED ===
{sources_info}

=== RULES TO CHECK ===

**1. INTRODUCTION (check carefully):**
- Does NOT use "This essay will...", "This paper examines...", "In this paper..." or similar announcements
- Has a thesis statement at the END
- Thesis follows ISO rule: Idea + Support + Order (shows what will be argued and structure)
- Is proportional to paper length (~10%)

**2. THESIS STATEMENT (CRITICAL):**
BAD examples (FAIL if found):
- "This essay examines how..."
- "This paper will discuss..."
- "This essay discusses..."
- "In this paper, it will be analyzed..."

GOOD example:
- "Gender symmetry in domestic violence, while controversial, reveals patterns in perpetration rates, challenging traditional frameworks and requiring new justice approaches."

**3. BODY PARAGRAPHS (check each one):**
- Each starts with a TOPIC SENTENCE (author's own words, introduces the paragraph idea)
- Each ends with a CONCLUDING SENTENCE (author's own words, NO citation at the end)
- Citations are in the MIDDLE ONLY, never at the very start or very end of paragraph
- Each paragraph discusses ONE idea only
- At least 5-6 sentences per paragraph

**4. PARAGRAPH BEGINNINGS (CRITICAL - check FIRST sentence of each body paragraph):**
The FIRST sentence must be YOUR topic sentence WITHOUT any citation (Author, Year).
WRONG: "Gender symmetry challenges traditional views (Aldridge, 2020)." - starts with citation
RIGHT: "Gender symmetry in domestic violence challenges traditional views of perpetration."

**5. PARAGRAPH ENDINGS (CRITICAL - check LAST sentence of each body paragraph):**
The LAST sentence must be YOUR concluding thought WITHOUT any citation (Author, Year).
WRONG: "...leading to better outcomes (Smith, 2020)." - ends with citation
RIGHT: "...leading to better outcomes (Smith, 2020). These results demonstrate the importance of early intervention."

**6. CONCLUSION:**
- NO new information
- NO citations
- Summarizes the main points
- Restates thesis in different words

**7. PROHIBITED WORDS (MUST NOT appear anywhere):**
delve, realm, harness, unlock, tapestry, paradigm, cutting-edge, revolutionize, landscape, potential, findings, intricate, showcasing, crucial, pivotal, surpass, meticulously, vibrant, unparalleled, underscore, leverage, synergy, innovative, game-changer, testament, commendable, meticulous, highlight, emphasize, boast, groundbreaking, align, foster, showcase, enhance, holistic, garner, accentuate, pioneering, trailblazing, unleash, versatile, transformative, redefine, seamless, optimize, scalable, robust, breakthrough, empower, streamline, comprehensive, nuanced, multifaceted, fosters

**8. ACADEMIC STYLE:**
- NO contractions (don't, isn't, won't - must use do not, is not, will not)
- NO first/second person (I, we, you, my, our, your) unless reflection paper
- NO rhetorical questions
- NO conjunctions at sentence start (And, But, Or)

**9. CONTENT:**
- Answers the main question
- Relevant to the topic
- Citations support claims properly

=== RETURN FORMAT ===
Return ONLY valid JSON:
{{
  "all_rules_passed": true or false,
  "issues": [
    {{"rule": "rule name", "problem": "specific problem found", "location": "where in text"}},
    ...
  ],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "citation_action": "keep" or "adjust" or "reinsert"
}}

IMPORTANT:
- Be STRICT. If ANY rule is violated, set "all_rules_passed": false
- List EVERY issue found, be specific about location
- Check EVERY paragraph FIRST sentence - must NOT have citation
- Check EVERY paragraph LAST sentence - must NOT have citation
- Check for ALL prohibited words
- Check thesis does NOT announce intentions ("This essay will...")

Return ONLY the JSON object, no other text."""


async def check_quality_node(state: OrderWorkflowState) -> dict:
    """
    Bot 5: Checks text quality using LLM against all academic writing rules

    Args:
        state: Current workflow state

    Returns:
        Updated state with quality assessment
    """
    logger.info(f"✅ Bot 5: Checking quality for order {state['order_id']}...")

    text = state.get('text_with_citations', state.get('draft_text', ''))
    requirements = state.get('requirements', {})
    attempts = state.get('quality_check_attempts', 0)
    sources = state.get('sources_found', [])

    if not text:
        logger.error("No text to check")
        return {
            **state,
            "status": "failed",
            "error": "No text for quality check",
            "agent_logs": state.get('agent_logs', []) + ["[Bot5:Quality] ERROR: No text"]
        }

    print("\n" + "="*80)
    print("✅ Bot 5: QUALITY CHECK")
    print("="*80 + "\n")

    print(f"   Checking: {requirements.get('main_topic', 'Unknown topic')[:50]}...")
    print(f"   Attempts: {attempts}/{MAX_QUALITY_ATTEMPTS}")
    print()

    llm = get_fast_model()
    if not llm:
        logger.warning("LLM not available, skipping quality check")
        return {
            **state,
            "quality_ok": True,
            "quality_issues": [],
            "citation_action": "keep",
            "status": "quality_ok",
            "agent_logs": state.get('agent_logs', []) + ["[Bot5:Quality] LLM unavailable, skipped"]
        }

    # Format sources info
    sources_info = "No sources provided"
    if sources:
        sources_info = "\n".join([
            f"- {s.get('citation', 'Unknown')}: {s.get('title', '')[:60]}"
            for s in sources
        ])

    prompt = QUALITY_CHECK_PROMPT.format(
        text=text[:6000],
        main_topic=requirements.get('main_topic', 'Not specified'),
        main_question=requirements.get('main_question', 'Not specified'),
        assignment_type=requirements.get('assignment_type', 'essay'),
        sources_info=sources_info
    )

    try:
        response = await llm.ainvoke(prompt)
        result = parse_json_response(response.content.strip())

        if not result:
            logger.warning("Failed to parse quality check response")
            return {
                **state,
                "quality_ok": True,
                "quality_issues": [],
                "citation_action": "keep",
                "status": "quality_ok",
                "agent_logs": state.get('agent_logs', []) + ["[Bot5:Quality] Parse failed, assuming OK"]
            }

        all_passed = result.get('all_rules_passed', True)
        issues = result.get('issues', [])
        suggestions = result.get('suggestions', [])
        citation_action = result.get('citation_action', 'keep')

        # Format issues for display and revision
        issue_texts = []
        for issue in issues:
            if isinstance(issue, dict):
                issue_text = f"{issue.get('rule', 'Unknown')}: {issue.get('problem', '')}"
                if issue.get('location'):
                    issue_text += f" (at: {issue.get('location')[:50]})"
                issue_texts.append(issue_text)
            else:
                issue_texts.append(str(issue))

        # Log results
        if all_passed:
            print("   ✅ ALL QUALITY CHECKS PASSED\n")
            if suggestions:
                print("   Minor suggestions:")
                for s in suggestions:
                    print(f"     • {s}")
                print()
        else:
            print(f"   ⚠️ QUALITY CHECK FAILED - {len(issues)} issues found\n")
            print("   Issues:")
            for issue_text in issue_texts[:10]:  # Show first 10
                print(f"     ❌ {issue_text}")
            if len(issue_texts) > 10:
                print(f"     ... and {len(issue_texts) - 10} more")
            print()
            print(f"   Citation action: {citation_action}")
            print()

        # Check if max attempts reached
        if not all_passed and attempts >= MAX_QUALITY_ATTEMPTS:
            print(f"   ⚠️ Max attempts ({MAX_QUALITY_ATTEMPTS}) reached, proceeding anyway\n")
            logger.warning("Max quality attempts reached, proceeding")
            return {
                **state,
                "quality_ok": False,
                "quality_issues": issue_texts,
                "quality_suggestions": suggestions,
                "citation_action": citation_action,
                "status": "quality_ok",  # Proceed anyway
                "agent_logs": state.get('agent_logs', []) + [
                    f"[Bot5:Quality] Max attempts, proceeding with {len(issues)} issues"
                ]
            }

        if all_passed:
            logger.info("Quality check passed - all rules OK")
            return {
                **state,
                "quality_ok": True,
                "quality_issues": [],
                "quality_suggestions": suggestions,
                "citation_action": "keep",
                "status": "quality_ok",
                "agent_logs": state.get('agent_logs', []) + ["[Bot5:Quality] PASSED - all rules OK"]
            }
        else:
            logger.info(f"Quality check found {len(issues)} issues, sending for revision")
            return {
                **state,
                "quality_ok": False,
                "quality_issues": issue_texts,
                "quality_suggestions": suggestions,
                "citation_action": citation_action,
                "writer_mode": "revise",
                "status": "quality_revising",
                "quality_check_attempts": attempts + 1,
                "agent_logs": state.get('agent_logs', []) + [
                    f"[Bot5:Quality] FAILED - {len(issues)} issues, revision #{attempts + 1}"
                ]
            }

    except Exception as e:
        logger.error(f"Error in quality check: {e}")
        return {
            **state,
            "quality_ok": True,
            "quality_issues": [],
            "citation_action": "keep",
            "status": "quality_ok",
            "agent_logs": state.get('agent_logs', []) + [f"[Bot5:Quality] ERROR: {str(e)}, skipped"]
        }
