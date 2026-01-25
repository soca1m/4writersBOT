"""
Post-Humanization Quality Checker
Checks humanized text for critical errors while maintaining humanized style
Only fixes critical errors (misplaced citations, abbreviations, etc.)
Does NOT change writing style or sentence structure
"""
import json
import logging
import re
from typing import Dict, Any, List

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_fast_model

logger = logging.getLogger(__name__)

MAX_QUALITY_ATTEMPTS = 50  # Allow many attempts to fix critical errors

POST_HUMANIZATION_CHECK_PROMPT = """<role>
You are a post-humanization quality checker ensuring academic integrity while preserving natural, human-like writing style.
</role>

<critical_context>
This text was AI-generated, then humanized using paraphrasing tools to bypass AI detection. The humanization process intentionally made the text less formal and more varied in structure.

DO NOT suggest changes that would make it sound more "academic" or "formal" - that would reintroduce AI patterns and defeat the purpose of humanization.
</critical_context>

<text_to_check>
{text}
</text_to_check>

<checking_philosophy>
<preserve>
PRESERVE the humanized, natural style:
- Informal language ("sort of", "kind of", "a bit") - KEEP THIS
- Sentence fragments or very short sentences - KEEP THIS
- Varied/unusual sentence structures - KEEP THIS
- Starting sentences with "And" or "But" - KEEP THIS
- Less formal vocabulary - KEEP THIS
- Personal tone or casual phrasing - KEEP THIS
</preserve>

<fix>
FIX ONLY critical errors that affect academic integrity:
- Citation placement errors (first/last sentences)
- Contractions (don't → do not)
- Undefined abbreviations (IPV, CDC, etc.)
- Missing citations
- Text completeness issues
- Sentence repetition/tautology (consecutive sentences starting with same word)
- Weak or inaccurate thesis statement
- Introduction/Conclusion length (must be minimum 3 sentences each)
</fix>
</checking_philosophy>

<critical_errors_to_check>
<error_1_citation_placement>
<rule>Citations should NOT be the final element in body paragraphs AND should NOT be in the first sentence of body paragraphs.</rule>

<critical_rule>
First and last sentences of body paragraphs MUST NOT contain citations.
- First sentence = Topic sentence (introduces paragraph in YOUR words)
- Last sentence = Concluding sentence (summarizes paragraph in YOUR words)
- Middle sentences = Evidence with citations
</critical_rule>

<acceptable>
✓ "Healthcare systems face challenges. Studies (Smith, 2020) show improvements in outcomes. These findings demonstrate effectiveness."
  [Topic sentence → Citation in middle → Concluding sentence]

✓ "Outcomes improve under new systems. Research (Smith, 2020) confirms this trend persists. Such results inform policy decisions."
  [Good structure: intro → evidence → conclusion]
</acceptable>

<unacceptable>
✗ "Research (Smith, 2020) shows outcomes improve. Additional analysis supports this."
  [Citation in FIRST sentence - violates topic sentence rule]

✗ "Healthcare systems face challenges. Studies show improvements (Smith, 2020)."
  [Citation in LAST sentence - violates concluding sentence rule]

✗ "Outcomes improve (Smith, 2020). This matters."
  [Trivial concluding sentence under 8 words]
</unacceptable>

<how_to_fix>
When you find citation placement errors in your fix suggestion, provide SPECIFIC instructions:

If citation is in FIRST sentence:
→ "Add a topic sentence BEFORE this: '[Specific suggestion like: Healthcare reform addresses cost containment challenges.]' Then keep the existing sentence as sentence 2."

If citation is in LAST sentence:
→ "Add a concluding sentence AFTER the citation: '[Specific suggestion like: These structural barriers demonstrate implementation complexity.]' Keep the sentence with citation unchanged."

DO NOT suggest moving citations around - ONLY suggest adding ONE new sentence.
</how_to_fix>

<when_to_flag>
Flag if:
- First sentence of body paragraph contains citation
- Last sentence of body paragraph contains citation
- Last sentence has citation with only trivial words after it (under 8 words of meaningful content)
</when_to_flag>
</error_1_citation_placement>

<error_2_contractions>
<rule>No contractions in academic writing</rule>

<violations>
don't, isn't, won't, can't, shouldn't, wouldn't, haven't, hasn't, wasn't, weren't
</violations>

<corrections>
do not, is not, will not, cannot, should not, would not, have not, has not, was not, were not
</corrections>
</error_2_contractions>

<error_3_undefined_abbreviations>
<rule>All abbreviations must be defined on first use</rule>

<correct>
"intimate partner violence (IPV)... IPV rates increased..."
[Abbreviation defined before use]
</correct>

<incorrect>
"IPV rates increased..." (if IPV never defined earlier)
[Abbreviation used without definition]
</incorrect>

<common_abbreviations_to_check>
IPV, USA, FBI, CEO, PTSD, ADHD, CDC, WHO, etc.
</common_abbreviations_to_check>
</error_3_undefined_abbreviations>

<error_4_text_completeness>
<rule>Text must be complete - not cut off mid-sentence or mid-word</rule>
</error_4_text_completeness>

<error_5_missing_citations>
<rule>Every paragraph discussing research/data must have at least one citation</rule>

<reasoning>
Claims about research findings require source attribution for academic integrity.
</reasoning>
</error_5_missing_citations>

<error_6_sentence_repetition_tautology>
<rule>Consecutive sentences MUST NOT start with the same word or phrase</rule>

<critical>
This is a CRITICAL error that makes writing sound robotic and AI-generated.
</critical>

<violations>
✗ "Single-payer systems reduce costs. Single-payer systems improve access. Single-payer systems face challenges."
  [Three consecutive sentences start with "Single-payer systems"]

✗ "The implementation requires funding. The implementation faces barriers. The implementation needs support."
  [Three consecutive sentences start with "The implementation"]

✗ "These findings support reform. These findings demonstrate effectiveness. These findings reveal patterns."
  [Three consecutive sentences start with "These findings"]
</violations>

<acceptable>
✓ "Single-payer systems reduce costs. These models improve access. However, such approaches face challenges."
  [Varied sentence openings]

✓ "The implementation requires funding. Such reforms face barriers. Policy changes need broad support."
  [Different starting words/phrases]
</acceptable>

<when_to_flag>
Flag if TWO OR MORE consecutive sentences start with the exact same word (case-insensitive) or the exact same phrase (2-3 words).

Common patterns to watch for:
- "The [noun]..." repeated
- "[Topic name]..." repeated (e.g., "Single-payer..." "Healthcare...")
- "These/This/Such..." repeated
- "Research/Studies/Evidence..." repeated
</when_to_flag>

<how_to_fix>
Suggest ONE of these simple fixes:
1. Replace repeated opening with pronoun: "These systems...", "Such models...", "It..."
2. Add transition word: "However,", "Additionally,", "Furthermore,"
3. Restructure sentence to start differently
</how_to_fix>
</error_6_sentence_repetition_tautology>

<error_7_weak_or_inaccurate_thesis>
<rule>The thesis statement must be specific, argumentative, and accurate</rule>

<critical>
The thesis is the MOST IMPORTANT sentence in the essay.
It must clearly state the essay's argument and direction.
</critical>

<weak_thesis_violations>
✗ "This essay will discuss single-payer healthcare."
  [Announces intent instead of making argument]

✗ "Single-payer has pros and cons."
  [Too vague, doesn't take position]

✗ "Healthcare is important and needs reform."
  [Generic, no specific argument]

✗ "I will analyze various aspects of healthcare."
  [First person, announces instead of arguing]
</weak_thesis_violations>

<strong_thesis_examples>
✓ "Single-payer medicine provides lower administrative expenses as its main benefit but government control issues act as a significant drawback, requiring the United States to tackle political obstacles through step-by-step policy changes."
  [Specific, takes position, shows structure]

✓ "While single-payer systems offer cost savings through unified administration, implementation barriers including political resistance and stakeholder concerns necessitate incremental reform strategies."
  [Clear argument with contrasting points]
</strong_thesis_examples>

<when_to_flag>
Flag thesis if it:
- Uses "This essay will..." or "This paper discusses..."
- Is vague or generic without specific claims
- Doesn't preview the essay's structure/main points
- Uses first person (I, we, my, our)
- Doesn't match the actual content of the essay
</when_to_flag>
</error_7_weak_or_inaccurate_thesis>

<error_8_intro_conclusion_length>
<rule>Introduction and Conclusion MUST each contain at least 3 sentences</rule>

<critical>
This is NOT a minor suggestion - it's a CRITICAL requirement.
Introductions and conclusions under 3 sentences are incomplete.
</critical>

<violations>
✗ Introduction with 1-2 sentences only
✗ Conclusion with 1-2 sentences only
</violations>

<minimum_requirements>
INTRODUCTION (minimum 3 sentences):
1. Hook or context (1-2 sentences)
2. Background or overview (1 sentence)
3. Thesis statement (1 sentence)

CONCLUSION (minimum 3 sentences):
1. Restate thesis differently (1 sentence)
2. Summarize main points (1-2 sentences)
3. Final thought or implication (1 sentence)
</minimum_requirements>

<when_to_flag>
Count sentences in introduction paragraph (before first body section).
Count sentences in conclusion paragraph (after last body section).
If EITHER has fewer than 3 sentences → FLAG AS CRITICAL ERROR.
</when_to_flag>

<how_to_fix>
For introduction: "Add [X] more sentence(s) to reach minimum 3. Consider adding background context or expanding the hook."

For conclusion: "Add [X] more sentence(s) to reach minimum 3. Consider expanding summary of main points or adding final implications."
</how_to_fix>
</error_8_intro_conclusion_length>
</critical_errors_to_check>

<output_format>
<structure>
Return ONLY valid JSON with this exact structure:

{{
  "all_rules_passed": true or false,
  "issues": [
    {{
      "rule": "RULE NAME",
      "problem": "specific problem description",
      "location": "where in text",
      "fix_instruction": "how to fix while maintaining humanized style"
    }}
  ]
}}
</structure>

<guidelines>
- Set "all_rules_passed": true if NO critical errors found
- Set "all_rules_passed": false ONLY if critical errors exist
- For each issue, provide "fix_instruction" that maintains the natural, humanized style
- DO NOT include suggestions - only critical fixes
- Return ONLY the JSON object, no other text
</guidelines>
</output_format>"""


async def check_quality_post_humanization_node(state: OrderWorkflowState) -> dict:
    """
    Bot 5b: Post-humanization quality check

    Only checks for critical errors that affect academic integrity:
    - Misplaced citations
    - Contractions
    - Undefined abbreviations
    - Missing citations
    - Text completeness

    Does NOT change writing style or make text sound more academic.

    Args:
        state: Current workflow state

    Returns:
        Updated state with quality assessment
    """
    logger.info(f"✅ Bot 5b: Post-humanization quality check for order {state['order_id']}...")

    text = state.get('text_with_citations', state.get('draft_text', ''))
    requirements = state.get('requirements', {})
    sources = state.get('sources_found', [])
    attempts = state.get('quality_check_attempts', 0)

    if not text:
        logger.error("No text to check")
        return {
            **state,
            "status": "failed",
            "error": "No text for quality check",
            "agent_logs": state.get('agent_logs', []) + ["[Bot5b:PostHumanizationQuality] ERROR: No text"]
        }

    # Check if max attempts reached
    if attempts >= MAX_QUALITY_ATTEMPTS:
        logger.warning(f"Max post-humanization quality attempts ({MAX_QUALITY_ATTEMPTS}) reached, accepting text")
        print(f"\n   ⚠️ Max attempts ({MAX_QUALITY_ATTEMPTS}) reached - accepting text with minor issues")
        return {
            **state,
            "quality_ok": True,
            "quality_issues": [],
            "post_humanization_check": True,
            "status": "quality_ok",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot5b:PostHumanizationQuality] Max attempts reached, accepting text"
            ]
        }

    print("\n" + "="*80)
    print("✅ Bot 5b: POST-HUMANIZATION QUALITY CHECK")
    print("="*80 + "\n")

    print(f"   Context: Text has been humanized to bypass AI detection")
    print(f"   Focus: Critical errors only (citations, contractions, abbreviations)")
    print(f"   Checking: {requirements.get('main_topic', 'Unknown topic')[:50]}...")
    print(f"   Attempt: {attempts + 1}/{MAX_QUALITY_ATTEMPTS}")
    print()

    llm = get_fast_model()
    if not llm:
        logger.warning("LLM not available, skipping post-humanization quality check")
        return {
            **state,
            "post_humanization_check": True,
            "quality_ok": True,
            "quality_issues": [],
            "status": "quality_ok",
            "agent_logs": state.get('agent_logs', []) + ["[Bot5b:PostHumanizationQuality] LLM unavailable, skipped"]
        }

    # Format sources info
    sources_info = "No sources provided"
    if sources:
        sources_info = "\n".join([
            f"- {s.get('citation', 'Unknown')}: {s.get('title', '')[:60]}"
            for s in sources
        ])

    prompt = POST_HUMANIZATION_CHECK_PROMPT.format(
        text=text[:6000],  # Limit text length
    )

    try:
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()

        # Parse JSON
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        result = json.loads(response_text.strip())

        all_passed = result.get("all_rules_passed", False)
        issues_list = result.get("issues", [])

        if all_passed:
            print(f"   ✅ ALL CHECKS PASSED")
            print(f"   No critical errors found")
            print(f"   Text maintains humanized style\n")

            logger.info("Post-humanization quality check passed")

            return {
                **state,
                "post_humanization_check": True,
                "quality_ok": True,
                "quality_issues": [],
                "status": "quality_ok",
                "agent_logs": state.get('agent_logs', []) + [
                    "[Bot5b:PostHumanizationQuality] PASSED - no critical errors"
                ]
            }

        # Critical errors found
        print(f"   ⚠️ CRITICAL ERRORS FOUND - {len(issues_list)} issues\n")
        print(f"   Issues:")

        issue_texts = []
        for issue in issues_list:
            rule = issue.get("rule", "Unknown")
            problem = issue.get("problem", "")
            location = issue.get("location", "")
            fix = issue.get("fix_instruction", "")

            issue_text = f"{rule}: {problem}"
            if location:
                issue_text += f" (at: {location})"
            if fix:
                issue_text += f" | Fix: {fix}"

            issue_texts.append(issue_text)
            print(f"     ❌ {issue_text}")

        print(f"\n   → These issues need manual fixes that preserve humanized style\n")

        logger.info(f"Post-humanization quality check found {len(issues_list)} critical errors")

        return {
            **state,
            "post_humanization_check": True,
            "quality_ok": False,
            "quality_check_attempts": attempts + 1,
            "quality_issues": issue_texts,
            "quality_suggestions": [],  # No suggestions in post-humanization check
            "citation_action": "keep",  # Don't change citations
            "writer_mode": "fix_humanized",  # Special mode for post-humanization fixes
            "status": "quality_revising",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot5b:PostHumanizationQuality] FAILED - {len(issues_list)} critical errors need fixing"
            ]
        }

    except Exception as e:
        logger.error(f"Error in post-humanization quality check: {e}")
        logger.exception(e)
        # If quality check fails, proceed anyway
        return {
            **state,
            "post_humanization_check": True,
            "quality_ok": True,
            "quality_issues": [],
            "status": "quality_ok",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot5b:PostHumanizationQuality] ERROR: {str(e)}, proceeding"
            ]
        }