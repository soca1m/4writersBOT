"""
Writer Mode Strategy Classes - Strategy Pattern

Each mode is a separate class responsible for ONE specific writing task:
- InitialMode: Write initial draft
- ExpandMode: Add content to reach word count
- ShortenMode: Reduce content to meet limit
- ReviseMode: Fix quality issues
- FixHumanizedMode: Fix post-humanization errors

This follows:
- Single Responsibility: Each class has one job
- Open/Closed: Easy to add new modes without modifying existing ones
- Strategy Pattern: Different algorithms (modes) for the same task (writing)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

from src.workflows.state import OrderWorkflowState
from src.agents.base_agent import PromptBasedAgent
from src.services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


def count_words(text: str) -> int:
    """Count words in text, excluding citations and references"""
    if not text:
        return 0

    # Remove common reference section markers
    for marker in ["References", "Bibliography", "Works Cited", "---"]:
        if marker in text:
            text = text[:text.find(marker)]

    # Remove citations (Author, Year) and (Author et al., Year)
    import re
    text = re.sub(r'\([A-Z][a-zA-Z\s&,]+\d{4}\)', '', text)

    # Count words
    words = text.split()
    return len([w for w in words if w.strip()])


class WriterMode(ABC):
    """
    Abstract base class for writer modes

    Each mode implements a specific writing strategy
    """

    def __init__(self, prompt_file: str):
        """
        Initialize mode

        Args:
            prompt_file: Name of prompt file (without .txt extension)
        """
        self.prompt_file = prompt_file
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def execute(
        self,
        state: OrderWorkflowState,
        llm,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the writing mode

        Args:
            state: Current workflow state
            llm: Language model instance
            requirements: Writing requirements

        Returns:
            Updated state dict
        """
        pass

    def load_prompt_template(self) -> str:
        """Load prompt template from file"""
        return PromptManager.load(self.prompt_file)

    async def invoke_llm(self, llm, prompt: str) -> str:
        """Invoke LLM with error handling"""
        try:
            response = await llm.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            self.logger.error(f"LLM invocation error: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """Remove unwanted additions like References section"""
        for marker in ["References", "Bibliography", "Works Cited"]:
            if marker in text:
                text = text[:text.find(marker)].strip()
        return text


class InitialMode(WriterMode):
    """Write initial draft from scratch"""

    def __init__(self):
        super().__init__("writer_prompt")

    async def execute(
        self,
        state: OrderWorkflowState,
        llm,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Write initial draft"""
        self.logger.info("Writing initial draft...")

        print("\n" + "="*80)
        print("✍️ Bot 2: WRITING INITIAL TEXT...")
        print("="*80 + "\n")

        # Load main writer prompt
        template = self.load_prompt_template()

        # Format with requirements
        prompt = PromptManager.format(
            template,
            assignment_type=requirements.get('assignment_type', 'essay'),
            main_topic=requirements.get('main_topic', 'Not specified'),
            main_question=requirements.get('main_question', 'Not specified'),
            target_word_count=requirements.get('target_word_count', 300),
            required_sources=requirements.get('required_sources', 2),
            files_content=state.get('files_content', 'No files attached'),
            specific_instructions=requirements.get('specific_instructions', 'None'),
            sources_found="Sources will be added by Bot 3 (Citation Integrator)"
        )

        # Invoke LLM
        draft_text = await self.invoke_llm(llm, prompt)

        if not draft_text:
            return {
                **state,
                "status": "failed",
                "error": "Failed to generate initial draft"
            }

        draft_text = self.clean_text(draft_text)
        word_count = count_words(draft_text)

        print(f"📝 Initial draft written: {word_count} words")
        print(f"   Target: {requirements.get('target_word_count', 300)} words")
        print(f"   ✅ Meets target\n")

        return {
            **state,
            "draft_text": draft_text,
            "word_count": word_count,
            "writer_mode": "initial",
            "status": "text_written",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot2:Writer] Initial draft: {word_count} words"
            ]
        }


class ExpandMode(WriterMode):
    """Expand text to reach minimum word count"""

    def __init__(self):
        super().__init__("writer_expand_prompt")

    async def execute(
        self,
        state: OrderWorkflowState,
        llm,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Expand text"""
        current_text = state.get('draft_text', '')
        current_words = count_words(current_text)
        target_words = requirements.get('target_word_count', 300)
        words_needed = target_words - current_words

        self.logger.info(f"Expanding text: {current_words} → {target_words} words")

        print("\n" + "="*80)
        print(f"✍️ Bot 2: EXPANDING TEXT (+{words_needed} words needed)...")
        print("="*80 + "\n")

        template = self.load_prompt_template()
        prompt = PromptManager.format(
            template,
            current_text=current_text,
            current_words=current_words,
            target_words=target_words,
            words_needed=words_needed,
            main_topic=requirements.get('main_topic', 'Not specified'),
            main_question=requirements.get('main_question', 'Not specified')
        )

        expanded_text = await self.invoke_llm(llm, prompt)

        if not expanded_text:
            return {
                **state,
                "status": "failed",
                "error": "Failed to expand text"
            }

        expanded_text = self.clean_text(expanded_text)
        new_word_count = count_words(expanded_text)

        print(f"📝 Text expanded: {current_words} → {new_word_count} words")
        print(f"   Target: {target_words} words")
        status_msg = "✅ Meets target" if new_word_count >= target_words else "⚠️ Still below target"
        print(f"   {status_msg}\n")

        return {
            **state,
            "draft_text": expanded_text,
            "word_count": new_word_count,
            "writer_mode": "expand",
            "word_count_attempts": state.get('word_count_attempts', 0) + 1,
            "status": "text_written",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot2:Writer] Expanded: {current_words} → {new_word_count} words"
            ]
        }


class ShortenMode(WriterMode):
    """Shorten text to meet maximum word count"""

    def __init__(self):
        super().__init__("writer_shorten_prompt")

    async def execute(
        self,
        state: OrderWorkflowState,
        llm,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Shorten text"""
        current_text = state.get('text_with_citations', state.get('draft_text', ''))
        current_words = count_words(current_text)
        pages_required = requirements.get('pages', state.get('pages_required', 1))

        # Calculate maximum
        target_words = requirements.get('target_word_count', 300)
        if pages_required <= 4:
            max_words = int(target_words * 1.40)
        else:
            max_words = int(target_words * 1.10)

        words_to_cut = current_words - max_words

        self.logger.info(f"Shortening text: {current_words} → {max_words} max")

        print("\n" + "="*80)
        print(f"✍️ Bot 2: SHORTENING TEXT (-{words_to_cut} words to cut)...")
        print("="*80 + "\n")

        template = self.load_prompt_template()
        prompt = PromptManager.format(
            template,
            current_text=current_text,
            current_words=current_words,
            max_words=max_words,
            words_to_cut=words_to_cut,
            main_topic=requirements.get('main_topic', 'Not specified'),
            main_question=requirements.get('main_question', 'Not specified')
        )

        shortened_text = await self.invoke_llm(llm, prompt)

        if not shortened_text:
            return {
                **state,
                "status": "failed",
                "error": "Failed to shorten text"
            }

        shortened_text = self.clean_text(shortened_text)
        new_word_count = count_words(shortened_text)

        print(f"📝 Text shortened: {current_words} → {new_word_count} words")
        print(f"   Maximum: {max_words} words")
        status_msg = "✅ Within limit" if new_word_count <= max_words else "⚠️ Still over limit"
        print(f"   {status_msg}\n")

        return {
            **state,
            "draft_text": shortened_text,
            "text_with_citations": shortened_text,
            "word_count": new_word_count,
            "writer_mode": "shorten",
            "word_count_attempts": state.get('word_count_attempts', 0) + 1,
            "status": "text_written",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot2:Writer] Shortened: {current_words} → {new_word_count} words"
            ]
        }


class ReviseMode(WriterMode):
    """Revise text to fix quality issues"""

    def __init__(self):
        super().__init__("writer_revise_prompt")

    def get_citation_instructions(self, citation_action: str) -> str:
        """
        Get citation handling instructions based on action

        Args:
            citation_action: "keep", "adjust", or "reinsert"

        Returns:
            Instruction text
        """
        if citation_action == "keep":
            return "KEEP all existing citations exactly as they are (Author, Year). Do not remove or change them."
        elif citation_action == "adjust":
            return PromptManager.load("citation_placement_fix_instructions")
        elif citation_action == "reinsert":
            return "Citations will be re-added later. Focus only on the text content."
        else:
            return ""

    async def execute(
        self,
        state: OrderWorkflowState,
        llm,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Revise text based on quality feedback"""
        current_text = state.get('text_with_citations', state.get('draft_text', ''))
        quality_issues = state.get('quality_issues', [])
        quality_suggestions = state.get('quality_suggestions', [])
        citation_action = state.get('citation_action', 'keep')

        target_words = state.get('target_word_count', requirements.get('target_word_count', 300))
        current_words = count_words(current_text)

        self.logger.info(f"Revising text: {len(quality_issues)} issues, {len(quality_suggestions)} suggestions")

        print("\n" + "="*80)
        print("✍️ Bot 2: REVISING TEXT BASED ON QUALITY FEEDBACK...")
        print("="*80 + "\n")

        # Format issues and suggestions
        issues_text = "\n".join([f"- {issue}" for issue in quality_issues]) if quality_issues else "None"
        suggestions_text = "\n".join([f"- {s}" for s in quality_suggestions]) if quality_suggestions else "None"

        # Get citation instructions
        citation_instructions = self.get_citation_instructions(citation_action)

        # Calculate word count limits
        pages_required = requirements.get('pages', 1)
        if pages_required <= 4:
            max_words = int(target_words * 1.40)
        else:
            max_words = int(target_words * 1.10)

        words_over_limit = current_words - max_words

        # Build word count warning
        word_count_warning = ""
        if words_over_limit > 0:
            word_count_warning = f"""🚨 CRITICAL WORD COUNT VIOLATION 🚨
Current: {current_words} words
Maximum allowed: {max_words} words
You are {words_over_limit} words OVER the limit!

YOU MUST reduce word count to {max_words} words or less while fixing issues.
DO NOT add new sentences. ONLY modify existing sentences minimally."""
        elif current_words > target_words:
            words_over_target = current_words - target_words
            word_count_warning = f"""⚠️ WORD COUNT WARNING
Current: {current_words} words
Target: {target_words} words
Maximum: {max_words} words

You are {words_over_target} words over target. DO NOT add more text.
Fix issues by MODIFYING existing sentences, not adding new ones."""

        # Load and format template
        template = self.load_prompt_template()
        prompt = PromptManager.format(
            template,
            current_text=current_text,
            current_words=current_words,
            word_count_warning=word_count_warning,
            issues_text=issues_text,
            suggestions_text=suggestions_text,
            main_topic=requirements.get('main_topic', 'Not specified'),
            main_question=requirements.get('main_question', 'Not specified'),
            target_words=target_words,
            max_words=max_words,
            citation_instructions=citation_instructions
        )

        # Invoke LLM
        revised_text = await self.invoke_llm(llm, prompt)

        if not revised_text:
            return {
                **state,
                "status": "failed",
                "error": "Failed to revise text"
            }

        revised_text = self.clean_text(revised_text)
        word_count = count_words(revised_text)

        total_changes = len(quality_issues) + len(quality_suggestions)
        print(f"📝 Text revised: {word_count} words")
        print(f"   Critical issues fixed: {len(quality_issues)}")
        print(f"   Suggestions applied: {len(quality_suggestions)}")
        print(f"   Total improvements: {total_changes}")

        # Debug output for citation issues
        if citation_action == "adjust" and quality_issues:
            citation_issues = [issue for issue in quality_issues if "CITATION" in issue.upper()]
            if citation_issues:
                print(f"\n   🔍 DEBUG - Citation issues that should be fixed:")
                for issue in citation_issues:
                    print(f"      {issue}")

                # Show last part of revised text
                print(f"\n   📄 Last part of revised text:")
                paragraphs = revised_text.split('\n\n')
                for i, para in enumerate(paragraphs[-3:], start=len(paragraphs)-2):
                    if para.strip():
                        last_sentences = para.split('. ')[-2:]
                        preview = '. '.join(last_sentences)
                        if len(preview) > 150:
                            preview = '...' + preview[-150:]
                        print(f"      Para {i}: ...{preview}")
                print()

        # Check if exceeded limit
        if word_count > max_words:
            words_over = word_count - max_words
            print(f"   ⚠️ EXCEEDED LIMIT by {words_over} words - auto-shortening...\n")

            return {
                **state,
                "draft_text": revised_text,
                "text_with_citations": revised_text,
                "word_count": word_count,
                "writer_mode": "revise",
                "status": "word_count_shortening",
                "agent_logs": state.get('agent_logs', []) + [
                    f"[Bot2:Writer] Revised but over limit: {word_count}/{max_words}"
                ]
            }

        return {
            **state,
            "draft_text": revised_text,
            "text_with_citations": revised_text,
            "word_count": word_count,
            "writer_mode": "revise",
            "status": "text_revised",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot2:Writer] Revised: {len(quality_issues)} issues fixed"
            ]
        }


class FixHumanizedMode(WriterMode):
    """Fix critical errors in humanized text while preserving natural style"""

    def __init__(self):
        super().__init__("writer_fix_humanized_prompt")

    async def execute(
        self,
        state: OrderWorkflowState,
        llm,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fix humanized text"""
        current_text = state.get('text_with_citations', state.get('draft_text', ''))
        text_before_humanization = state.get('text_before_humanization', '')
        quality_issues = state.get('quality_issues', [])

        self.logger.info(f"Fixing humanized text: {len(quality_issues)} critical issues")

        print("\n" + "="*80)
        print("✍️ Bot 2: FIXING HUMANIZED TEXT (PRESERVING NATURAL STYLE)...")
        print("="*80 + "\n")

        issues_text = "\n".join([f"- {issue}" for issue in quality_issues]) if quality_issues else "None"

        template = self.load_prompt_template()
        prompt = PromptManager.format(
            template,
            current_text=current_text,
            text_before_humanization=text_before_humanization[:500] + "..." if text_before_humanization else "Not available",
            issues_text=issues_text,
            main_topic=requirements.get('main_topic', 'Not specified'),
            main_question=requirements.get('main_question', 'Not specified')
        )

        fixed_text = await self.invoke_llm(llm, prompt)

        if not fixed_text:
            return {
                **state,
                "status": "failed",
                "error": "Failed to fix humanized text"
            }

        fixed_text = self.clean_text(fixed_text)
        word_count = count_words(fixed_text)

        print(f"📝 Text fixed: {word_count} words")
        print(f"   Critical issues fixed: {len(quality_issues)}")
        print(f"   ✅ Natural style preserved\n")

        return {
            **state,
            "draft_text": fixed_text,
            "text_with_citations": fixed_text,
            "word_count": word_count,
            "writer_mode": "fix_humanized",
            "status": "text_revised",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot2:Writer] Fixed humanized text: {len(quality_issues)} issues"
            ]
        }
