"""
Bot 1: Requirements Analyzer
Извлекает структурированные требования из описания задания
Возвращает JSON с темой, структурой, количеством слов и источников
"""
import json
import logging
import re
from typing import Dict, Any

from src.agents.base_agent import PromptBasedAgent
from src.services.prompt_manager import PromptManager
from src.workflows.state import OrderWorkflowState
from src.utils.file_parser import parse_multiple_files

logger = logging.getLogger(__name__)


class RequirementsAnalyzer(PromptBasedAgent):
    """Agent that analyzes order requirements and extracts structured data"""

    def __init__(self):
        super().__init__(
            agent_name="Bot1:Requirements",
            prompt_file="requirements_extractor_prompt.txt"
        )

    def parse_json_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        if not text:
            return {}

        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON between { and }
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {}

    def parse_files(self, state: OrderWorkflowState) -> str:
        """Parse attached files and return content"""
        files_content = ""
        if state.get('attached_files'):
            logger.info(f"Parsing {len(state['attached_files'])} attached files...")
            files_content = parse_multiple_files(state['attached_files'])
            logger.info(f"Extracted {len(files_content)} characters from files")
        return files_content

    def print_results(self, requirements: Dict[str, Any], target_word_count: int):
        """Print extracted requirements in formatted output"""
        print("\n" + "="*80)
        print("📋 REQUIREMENTS EXTRACTED:\n")
        print(f"  Pages Detected: {requirements.get('pages', 0)}")
        print(f"  Type: {requirements.get('assignment_type', 'N/A')}")
        print(f"  Topic: {requirements.get('main_topic', 'N/A')}")
        print(f"  Main Question: {requirements.get('main_question', 'N/A')}")
        print(f"  Target Words: {target_word_count}")
        print(f"  Required Sources: {requirements.get('required_sources', 'N/A')}")
        print(f"  Search Keywords: {requirements.get('search_keywords', 'N/A')}")
        print(f"  Citation Style: {requirements.get('citation_style', 'APA')}")

        if requirements.get('structure'):
            print(f"\n  Structure:")
            struct = requirements['structure']
            print(f"    - Intro: {struct.get('introduction_words', 0)} words")
            for section in struct.get('body_sections', []):
                print(f"    - {section.get('heading', 'Section')}: {section.get('words', 0)} words")
            print(f"    - Conclusion: {struct.get('conclusion_words', 0)} words")

        if requirements.get('key_points'):
            print(f"\n  Key Points:")
            for point in requirements['key_points']:
                print(f"    • {point}")

        print("\n" + "="*80 + "\n")

    async def execute(self, state: OrderWorkflowState) -> Dict[str, Any]:
        """
        Analyze order requirements and extract structured data

        Args:
            state: Current workflow state

        Returns:
            Updated state with requirements
        """
        self.log_start(state['order_id'])

        # Parse attached files
        files_content = self.parse_files(state)

        # Load and format prompt
        prompt_template = self.load_prompt()
        prompt = PromptManager.format(
            prompt_template,
            order_description=state.get('order_description', 'Not specified'),
            files_content=files_content if files_content else "No files attached"
        )

        print("\n" + "="*80)
        print("🤖 Bot 1: ANALYZING REQUIREMENTS...")
        print("="*80 + "\n")

        # Invoke LLM
        response_text = await self.invoke_llm(prompt)

        # Parse JSON response
        requirements = self.parse_json_response(response_text)

        if not requirements:
            logger.error("Failed to parse JSON response")
            print(f"Raw response: {response_text[:500]}...")
            return self.update_state(
                state,
                status="failed",
                error="Failed to parse requirements JSON"
            )

        # Check if information is sufficient
        is_sufficient = requirements.get('is_sufficient', True)

        if not is_sufficient:
            missing = requirements.get('missing_info', 'Unknown')
            logger.warning(f"Insufficient information: {missing}")
            print(f"❌ INSUFFICIENT INFO: {missing}\n")
            return self.update_state(
                state,
                status="insufficient_info",
                error=f"Insufficient information: {missing}",
                requirements=requirements,
                parsed_files_content=files_content
            )

        # Calculate target word count from pages
        pages = requirements.get('pages_detected', 1)
        target_word_count = pages * 300

        # Add computed fields
        requirements['pages'] = pages
        requirements['target_word_count'] = target_word_count

        # Print results
        self.print_results(requirements, target_word_count)

        logger.info("✅ Requirements extracted successfully")

        return self.update_state(
            state,
            status="requirements_extracted",
            requirements=requirements,
            parsed_files_content=files_content,
            target_word_count=target_word_count
        )


# Node function for LangGraph workflow
async def analyze_requirements_node(state: OrderWorkflowState) -> dict:
    """
    Bot 1: Analyzes order requirements

    Args:
        state: Current workflow state

    Returns:
        Updated state with requirements
    """
    analyzer = RequirementsAnalyzer()
    return await analyzer.execute(state)
