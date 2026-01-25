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

MAX_QUALITY_ATTEMPTS = 50  # Increased to allow more iterations


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


QUALITY_CHECK_PROMPT = """You are an academic writing quality checker. Check this text for CRITICAL errors only.

=== TEXT TO CHECK ===
{text}

=== REQUIREMENTS ===
- Topic: {main_topic}
- Main question: {main_question}
- Assignment type: {assignment_type}

=== SOURCES USED ===
{sources_info}

=== CRITICAL ERRORS TO CHECK (MUST FIX) ===

**1. ANNOUNCEMENT PHRASES IN THESIS:**
FAIL if thesis contains these exact patterns:
- "This essay will..."
- "This paper examines..."
- "This paper discusses..."
- "In this paper..."
- "This essay examines..."

GOOD thesis example (declarative):
- "Gender symmetry in domestic violence reveals important patterns in perpetration rates, challenging traditional frameworks."

**2. PARAGRAPH CITATION PLACEMENT (check ONLY body paragraphs, NOT introduction or conclusion):**

<critical_rule>
FAIL if EITHER:
- The FIRST sentence of any body paragraph contains a citation (Author, Year), OR
- The LAST sentence of any body paragraph contains a citation (Author, Year)

FIRST sentence = Topic sentence (YOUR words only)
LAST sentence = Concluding sentence (YOUR words only)
Citations belong in MIDDLE sentences only
</critical_rule>

<how_to_check>
1. Identify all body paragraphs (skip Introduction and Conclusion sections)
2. For EACH body paragraph:
   a. Check the FIRST sentence - if it contains "(Author, Year)" → FAIL
   b. Check the LAST sentence - if it contains "(Author, Year)" → FAIL
3. Citations should ONLY appear in middle sentences
</how_to_check>

<examples>
❌ WRONG (FAIL - citation in FIRST sentence):
"Research shows (Smith, 2020) that outcomes improve. Additional analysis confirms this. These findings matter."
→ First sentence has citation! FAIL

❌ WRONG (FAIL - citation in LAST sentence):
"Healthcare systems face challenges. Research shows improvements (Smith, 2020). Wait times remain a concern. Studies confirm this pattern (Jones, 2021)."
→ Last sentence: "Studies confirm this pattern (Jones, 2021)." ← Contains citation! FAIL

✅ CORRECT (PASS - citations in MIDDLE only):
"Healthcare systems face multiple challenges. Research (Smith, 2020) shows significant improvements in outcomes. Studies (Jones, 2021) confirm this pattern persists. These findings highlight the need for continued reform."
→ First sentence: NO citation ✓
→ Middle sentences: Have citations ✓
→ Last sentence: NO citation ✓
→ PASS!

❌ WRONG (FAIL - citation at end):
"Single-payer systems reduce costs. Evidence demonstrates efficiency (Author, 2020)."
→ Last sentence ends with citation! FAIL

✅ CORRECT (PASS):
"Single-payer systems demonstrate cost reduction potential. Evidence (Author, 2020) confirms efficiency improvements. These benefits warrant further consideration."
→ First sentence: NO citation ✓
→ Last sentence: NO citation ✓
→ PASS!
</examples>

<error_format>
If you find a violation, report it in ONE of these formats:

For FIRST sentence violation:
{{"rule": "PARAGRAPH CITATION PLACEMENT", "problem": "First sentence of body paragraph contains citation: '[exact first sentence]'", "location": "[which section/paragraph]"}}

For LAST sentence violation:
{{"rule": "PARAGRAPH CITATION PLACEMENT", "problem": "Last sentence of body paragraph ends with citation: '[exact last sentence]'", "location": "[which section/paragraph]"}}
</error_format>

IMPORTANT: Check BOTH first AND last sentences of every body paragraph.

**3. TEXT COMPLETENESS:**
FAIL if text appears cut off or incomplete (ends mid-sentence or mid-word)

**4. PROHIBITED WORDS (check for these only):**
delve, realm, harness, unlock, tapestry, paradigm, leverage, synergy, showcase, enhance, holistic, garner, accentuate, pioneering, trailblazing, unleash, transformative, redefine, seamless, optimize, scalable, robust, empower, streamline

Other words like "findings," "crucial," "potential," "innovative" are ACCEPTABLE if used moderately.

**5. CONTRACTIONS:**
FAIL if contains: don't, isn't, won't, can't, shouldn't, wouldn't (must use: do not, is not, will not, cannot, should not, would not)

**6. FIRST/SECOND PERSON:**
FAIL if contains: I, We, You, My, Our, Your (unless assignment type is "reflection" or explicitly allows it)

**7. PHRASAL VERBS:**
FAIL if uses phrasal verbs instead of formal verbs:
WRONG: "look at," "look into," "get rid of," "carry on," "put off," "hand out," "set up," "find out," "put up with," "think about," "come up with," "bring up," "take over," "figure out"
RIGHT: "examine," "investigate," "eliminate," "continue," "postpone," "distribute," "establish," "discover," "tolerate," "consider," "develop," "mention," "assume," "determine"

=== QUALITY ISSUES TO NOTE (but don't fail paper) ===
- Thesis could be stronger (mention if ISO structure unclear)
- Introduction length not ideal
- Paragraphs could be more balanced
- Citations could be distributed better
- Overly long sentences (40+ words) - should break into shorter sentences
- Section headings too long (should be 2-4 words)
- Section headings not parallel in structure
- Paper title too long or has unnecessary punctuation (colons, commas)
- Repetitive sentence openings: Multiple consecutive sentences start with the same word/phrase (e.g., "Single-payer systems... Single-payer systems... Single-payer systems..." or "The implementation... The implementation...")

=== DO NOT CHECK FOR (these are handled by other agents) ===
- Reference list presence - Bot 7 (References Generator) adds this automatically at the end
- Number of sources - Bot 3 (Citation Integrator) handles source count
- In-text citation format - as long as citations exist in (Author, Year) format, they're fine

=== RETURN FORMAT ===
Return ONLY valid JSON:
{{
  "all_rules_passed": true or false,
  "issues": [
    {{"rule": "RULE NAME", "problem": "specific problem", "location": "where"}},
    ...
  ],
  "suggestions": ["suggestion 1", "suggestion 2"],
  "citation_action": "keep" or "adjust" or "reinsert"
}}

EVALUATION APPROACH:
- Set "all_rules_passed": true if NO CRITICAL ERRORS found
- Set "all_rules_passed": false ONLY if CRITICAL ERRORS exist
- List ONLY ACTUAL ERRORS in "issues" array - DO NOT list rules that passed
- List minor suggestions in "suggestions" array (these don't fail the paper)

CITATION_ACTION DECISION:
Analyze the types of issues found and decide:
- "keep": No citation issues OR only minor style issues → keep existing citations unchanged
- "adjust": Only CITATION PLACEMENT issues (citations in wrong positions) → move citations to better locations without changing sources
- "reinsert": SOURCE CREDIBILITY/RELEVANCE issues (sources are inappropriate/irrelevant) → need to find completely new sources

IMPORTANT:
- If a rule is followed correctly, DO NOT mention it at all. Only report violations.
- Choose citation_action based on whether the SOURCES themselves are problematic (reinsert) or just their PLACEMENT (adjust)

Examples:
❌ WRONG: {{"rule": "CONTRACTIONS", "problem": "No contractions found - this rule is PASSED"}}
✅ CORRECT: (Don't mention it at all if no contractions found)

❌ WRONG: {{"rule": "FIRST PERSON", "problem": "No first/second person pronouns found - this rule is PASSED"}}
✅ CORRECT: (Don't mention it at all if rule is followed)

Be reasonable. Papers don't need to be perfect, just free of critical errors.

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
    print(f"   🔢 DEBUG: Starting quality check with attempts={attempts}")
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

        # Let LLM decide citation action based on the types of issues found
        citation_action = result.get('citation_action', 'keep')

        # Format issues for display and revision
        issue_texts = []
        for issue in issues:
            if isinstance(issue, dict):
                rule = issue.get('rule', 'Unknown')
                issue_text = f"{rule}: {issue.get('problem', '')}"
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
            # Check if we have suggestions to apply
            if suggestions and attempts == 0:
                # First pass with no critical errors but has suggestions - apply them
                new_attempts = attempts + 1
                logger.info(f"Quality check passed but found {len(suggestions)} suggestions, applying them (attempts: {attempts} → {new_attempts})")
                print(f"   🔢 DEBUG: No critical errors but applying {len(suggestions)} suggestions (attempts: {attempts} → {new_attempts})")
                return {
                    **state,
                    "quality_ok": False,  # Trigger revision to apply suggestions
                    "quality_issues": [],  # No critical issues
                    "quality_suggestions": suggestions,
                    "citation_action": "keep",
                    "writer_mode": "revise",
                    "status": "quality_revising",
                    "quality_check_attempts": new_attempts,
                    "agent_logs": state.get('agent_logs', []) + [
                        f"[Bot5:Quality] PASSED (critical) - applying {len(suggestions)} suggestions, revision #{new_attempts}"
                    ]
                }
            else:
                # No critical errors and either no suggestions OR already applied suggestions
                logger.info("Quality check passed - all rules OK")
                return {
                    **state,
                    "quality_ok": True,
                    "quality_issues": [],
                    "quality_suggestions": [],  # Clear suggestions after applying
                    "citation_action": "keep",
                    "status": "quality_ok",
                    "agent_logs": state.get('agent_logs', []) + ["[Bot5:Quality] PASSED - all rules OK"]
                }
        else:
            new_attempts = attempts + 1
            logger.info(f"Quality check found {len(issues)} issues, sending for revision (attempts: {attempts} → {new_attempts})")
            print(f"   🔢 DEBUG: Incrementing attempts: {attempts} → {new_attempts}")
            return {
                **state,
                "quality_ok": False,
                "quality_issues": issue_texts,
                "quality_suggestions": suggestions,
                "citation_action": citation_action,
                "writer_mode": "revise",
                "status": "quality_revising",
                "quality_check_attempts": new_attempts,
                "agent_logs": state.get('agent_logs', []) + [
                    f"[Bot5:Quality] FAILED - {len(issues)} issues, revision #{new_attempts}"
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
