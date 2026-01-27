"""
Bot 5: Quality Checker
Checks if text meets ALL academic writing requirements using LLM
Continues to send for revision until ALL issues are fixed
"""
import json
import logging
import re
from typing import Dict, Any

from src.agents.base_agent import PromptBasedAgent
from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_smart_model
from src.services.prompt_manager import PromptManager

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


class QualityChecker(PromptBasedAgent):
    """Agent that checks text quality against academic writing standards"""

    def __init__(self):
        super().__init__(
            agent_name="Bot5:Quality",
            llm_model=get_smart_model(use_reasoning=True),  # Use Sonnet 4.5 with reasoning
            prompt_file="quality_checker_prompt.txt"
        )

    async def execute(self, state: OrderWorkflowState) -> Dict[str, Any]:
        """
        Check text quality using LLM

        Args:
            state: Current workflow state

        Returns:
            Updated state with quality assessment
        """
        self.log_start(state['order_id'])

        text = state.get('text_with_citations', state.get('draft_text', ''))
        requirements = state.get('requirements', {})
        attempts = state.get('quality_check_attempts', 0)
        sources = state.get('sources_found', [])

        if not text:
            logger.error("No text to check")
            return self.update_state(
                state,
                status="failed",
                error="No text for quality check"
            )

        print("\n" + "="*80)
        print("✅ Bot 5: QUALITY CHECK")
        print("="*80 + "\n")

        print(f"   Checking: {requirements.get('main_topic', 'Unknown topic')[:50]}...")
        print(f"   Attempts: {attempts}/{MAX_QUALITY_ATTEMPTS}")
        print(f"   🔢 DEBUG: Starting quality check with attempts={attempts}")
        print()

        # Get LLM
        if not self.llm:
            self.llm = get_fast_model()

        if not self.llm:
            logger.warning("LLM not available, skipping quality check")
            return self.update_state(
                state,
                status="quality_ok",
                quality_ok=True,
                quality_issues=[],
                citation_action="keep"
            )

        # Format sources info with full abstracts for citation accuracy check
        sources_info = "No sources provided"
        if sources:
            sources_info = "\n\n".join([
                f"SOURCE {i}: {s.get('citation', 'Unknown')}\n"
                f"Title: {s.get('title', 'Unknown')}\n"
                f"Abstract: {s.get('abstract', 'No abstract available')}"
                for i, s in enumerate(sources, 1)
            ])

        # Load and format prompt with assignment-type support
        assignment_type = requirements.get('assignment_type', 'essay')
        citation_style = requirements.get('citation_style', 'APA')

        prompt_template = self.load_prompt(
            assignment_type=assignment_type,
            citation_style=citation_style
        )

        prompt = PromptManager.format(
            prompt_template,
            text=text,
            main_topic=requirements.get('main_topic', 'Not specified'),
            main_question=requirements.get('main_question', 'Not specified'),
            assignment_type=assignment_type,
            citation_style=citation_style,
            sources_info=sources_info
        )

        try:
            response = await self.invoke_llm(prompt)

            # Try to parse JSON
            result = parse_json_response(response)

            if not result:
                logger.error("Failed to parse quality check JSON response")
                print("\n   ❌ ERROR: Quality checker returned invalid JSON")
                print(f"\n   Raw response preview:\n{response[:1000]}\n")
                return self.update_state(
                    state,
                    status="failed",
                    error="Quality check failed - invalid JSON response from LLM"
                )

            all_passed = result.get('all_rules_passed', True)
            issues = result.get('issues', [])
            suggestions = result.get('suggestions', [])
            citation_action = result.get('citation_action', 'keep')

            # Format issues for display and revision
            issue_texts = []
            for issue in issues:
                if isinstance(issue, dict):
                    rule = issue.get('rule', 'Unknown')
                    citation = issue.get('citation_found', '')
                    problem = issue.get('problem', issue.get('sentence', ''))
                    issue_text = f"{rule}: {citation} - {problem}" if citation else f"{rule}: {problem}"
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

                self.log_success(f"Quality check passed (attempt {attempts})")

                return self.update_state(
                    state,
                    status="quality_ok",
                    quality_ok=True,
                    quality_issues=[],
                    quality_suggestions=suggestions,
                    citation_action="keep"
                )
            else:
                # Failed - has issues
                print(f"   ⚠️ QUALITY CHECK FAILED - {len(issues)} issues found\n")
                print(f"   Issues:")
                for issue in issue_texts:
                    print(f"     ❌ {issue}")
                print()

                if suggestions:
                    print(f"   Suggestions:")
                    for s in suggestions:
                        print(f"     💡 {s}")
                    print()

                print(f"   Citation action: {citation_action}\n")

                # Check max attempts
                if attempts >= MAX_QUALITY_ATTEMPTS:
                    logger.warning(f"Max quality attempts ({MAX_QUALITY_ATTEMPTS}) reached")
                    print(f"   ⚠️ Max attempts reached ({MAX_QUALITY_ATTEMPTS}), accepting current version\n")

                    return self.update_state(
                        state,
                        status="quality_ok",
                        quality_ok=True,  # Accept it
                        quality_issues=[],
                        quality_suggestions=[]
                    )

                # Increment attempts
                print(f"   🔢 DEBUG: Incrementing attempts: {attempts} → {attempts + 1}\n")

                logger.info(f"Quality issues found: {len(issues)}")

                return self.update_state(
                    state,
                    status="quality_revising",
                    quality_ok=False,
                    quality_issues=issue_texts,
                    quality_suggestions=suggestions,
                    citation_action=citation_action,
                    quality_check_attempts=attempts + 1,
                    writer_mode="revise"  # SET WRITER MODE TO REVISE
                )

        except Exception as e:
            logger.error(f"Quality check error: {e}")
            return self.update_state(
                state,
                status="quality_ok",  # Continue anyway
                quality_ok=True,
                quality_issues=[],
                citation_action="keep"
            )


async def check_quality_node(state: OrderWorkflowState) -> dict:
    """
    LangGraph node wrapper for quality checker

    Args:
        state: Current workflow state

    Returns:
        Updated state dict
    """
    checker = QualityChecker()
    return await checker.execute(state)
