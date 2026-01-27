"""
Prompt Management Service - DRY principle

Centralizes all prompt loading, caching, and formatting
Supports assignment-type and citation-style specific prompts
"""
from pathlib import Path
from typing import Dict, Optional
import logging
from src.utils.prompt_selector import get_prompt_selector

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"


class PromptManager:
    """
    Manages prompt templates for all agents

    Features:
    - Caching: Load prompts once, reuse many times
    - Validation: Check if files exist
    - Formatting: Helper methods for variable substitution
    """

    _instance = None
    _cache: Dict[str, str] = {}

    def __new__(cls):
        """Singleton pattern - one instance for entire app"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(
        cls,
        prompt_name: str,
        assignment_type: Optional[str] = None,
        citation_style: Optional[str] = None
    ) -> str:
        """
        Load prompt template by name with assignment-type and citation-style support

        Args:
            prompt_name: Name of prompt file (without .txt extension)
            assignment_type: Type of assignment (essay, discussion_post, research_paper)
            citation_style: Citation style (APA, MLA, Chicago, Harvard)

        Returns:
            Prompt template content

        Example:
            >>> PromptManager.load("writer_prompt", assignment_type="essay", citation_style="APA")
            "You are an academic writer..."
        """
        # Create cache key including type and style
        cache_key = f"{prompt_name}_{assignment_type or 'default'}_{citation_style or 'default'}"

        # Check cache first
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # Use PromptSelector for intelligent prompt loading
        selector = get_prompt_selector()

        try:
            content = selector.load_prompt(prompt_name, assignment_type, citation_style)
            cls._cache[cache_key] = content
            logger.debug(f"Loaded and cached prompt: {prompt_name} (type={assignment_type}, style={citation_style})")
            return content
        except FileNotFoundError as e:
            # Fallback to legacy location if PromptSelector fails
            logger.warning(f"PromptSelector failed, trying legacy location: {e}")
            prompt_file = PROMPTS_DIR / f"{prompt_name}.txt"

            if not prompt_file.exists():
                logger.error(f"Prompt file not found in legacy location: {prompt_file}")
                return ""

            try:
                content = prompt_file.read_text(encoding='utf-8')
                cls._cache[cache_key] = content
                return content
            except Exception as load_error:
                logger.error(f"Error loading prompt {prompt_name}: {load_error}")
                return ""

    @classmethod
    def format(cls, template: str, **variables) -> str:
        """
        Format template with variables using simple placeholder replacement

        Args:
            template: Template string
            **variables: Variables to substitute

        Returns:
            Formatted string

        Example:
            >>> template = "Hello {name}, you are {age} years old"
            >>> PromptManager.format(template, name="Alice", age=25)
            "Hello Alice, you are 25 years old"
        """
        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result

    @classmethod
    def clear_cache(cls):
        """Clear prompt cache (useful for testing)"""
        cls._cache.clear()
        logger.debug("Prompt cache cleared")


# Convenience functions for common prompts
def get_writer_prompt() -> str:
    """Get main writer prompt template"""
    return PromptManager.load("writer_prompt")


def get_requirements_prompt() -> str:
    """Get requirements analyzer prompt"""
    return PromptManager.load("requirements_extractor_prompt")


def get_researcher_prompt() -> str:
    """Get researcher prompt for query generation"""
    return PromptManager.load("researcher_prompt")


def get_rewriter_prompt() -> str:
    """Get rewriter prompt"""
    return PromptManager.load("rewriter_prompt")


def get_analyzer_prompt() -> str:
    """Get analyzer prompt"""
    return PromptManager.load("analyzer_prompt")
