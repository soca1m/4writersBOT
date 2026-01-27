"""
Prompt Selector - Dynamic prompt selection based on assignment type and citation style
Follows SOLID principles:
- Single Responsibility: Only handles prompt selection logic
- Open/Closed: Easy to add new assignment types without modifying existing code
- Dependency Inversion: Depends on abstractions (assignment type strings) not concrete implementations
"""
import os
from typing import Optional, Dict
from pathlib import Path


class PromptSelector:
    """
    Selects appropriate prompts based on assignment type and citation style.

    Supports:
    - Multiple assignment types (essay, discussion_post, research_paper)
    - Multiple citation styles (APA, MLA, Chicago, Harvard)
    - Fallback to default prompts if specific type not found
    """

    # Assignment type mappings (normalized)
    ASSIGNMENT_TYPE_MAP = {
        'essay': 'essay',
        'paper': 'essay',
        'research paper': 'research_paper',
        'research': 'research_paper',
        'discussion post': 'discussion_post',
        'discussion': 'discussion_post',
        'forum post': 'discussion_post',
        'coursework': 'essay',
        'term paper': 'research_paper',
    }

    # Citation style mappings (normalized)
    CITATION_STYLE_MAP = {
        'apa': 'APA',
        'mla': 'MLA',
        'chicago': 'Chicago',
        'harvard': 'Harvard',
        'turabian': 'Chicago',  # Turabian is based on Chicago
    }

    def __init__(self, prompts_base_dir: str = "/home/user/4writersBOT/prompts"):
        """
        Initialize PromptSelector

        Args:
            prompts_base_dir: Base directory containing all prompts
        """
        self.prompts_base_dir = Path(prompts_base_dir)
        self.assignment_types_dir = self.prompts_base_dir / "assignment_types"
        self.citation_styles_dir = self.prompts_base_dir / "citation_styles"
        self.shared_dir = self.prompts_base_dir / "shared"

    def normalize_assignment_type(self, assignment_type: str) -> str:
        """
        Normalize assignment type to standard format

        Args:
            assignment_type: Raw assignment type from order

        Returns:
            Normalized assignment type (essay, discussion_post, research_paper)
        """
        normalized = assignment_type.lower().strip()
        return self.ASSIGNMENT_TYPE_MAP.get(normalized, 'essay')  # Default to essay

    def normalize_citation_style(self, citation_style: str) -> str:
        """
        Normalize citation style to standard format

        Args:
            citation_style: Raw citation style from order

        Returns:
            Normalized citation style (APA, MLA, Chicago, Harvard)
        """
        normalized = citation_style.lower().strip()
        return self.CITATION_STYLE_MAP.get(normalized, 'APA')  # Default to APA

    def get_prompt_path(
        self,
        prompt_name: str,
        assignment_type: Optional[str] = None,
        citation_style: Optional[str] = None
    ) -> Path:
        """
        Get path to appropriate prompt file based on assignment type

        Priority order:
        1. Assignment-specific prompt: prompts/assignment_types/{type}/{prompt_name}.txt
        2. Shared prompt: prompts/shared/{prompt_name}.txt
        3. Legacy prompt: prompts/{prompt_name}.txt

        Args:
            prompt_name: Name of the prompt (without .txt extension)
            assignment_type: Type of assignment (essay, discussion_post, etc.)
            citation_style: Citation style (APA, MLA, etc.) - for future use

        Returns:
            Path to the prompt file
        """
        # Normalize assignment type
        if assignment_type:
            assignment_type = self.normalize_assignment_type(assignment_type)

        # Try assignment-specific prompt first
        if assignment_type:
            assignment_specific_path = (
                self.assignment_types_dir / assignment_type / f"{prompt_name}.txt"
            )
            if assignment_specific_path.exists():
                return assignment_specific_path

        # Try shared prompt
        shared_path = self.shared_dir / f"{prompt_name}.txt"
        if shared_path.exists():
            return shared_path

        # Fallback to legacy location (root prompts folder)
        legacy_path = self.prompts_base_dir / f"{prompt_name}.txt"
        if legacy_path.exists():
            return legacy_path

        # If nothing found, return expected path (will cause error with helpful message)
        return self.assignment_types_dir / assignment_type / f"{prompt_name}.txt"

    def load_prompt(
        self,
        prompt_name: str,
        assignment_type: Optional[str] = None,
        citation_style: Optional[str] = None
    ) -> str:
        """
        Load prompt content with dynamic citation style substitution

        Args:
            prompt_name: Name of the prompt
            assignment_type: Type of assignment
            citation_style: Citation style (will replace {citation_style} placeholder)

        Returns:
            Prompt content with substitutions applied

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        prompt_path = self.get_prompt_path(prompt_name, assignment_type, citation_style)

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}\n"
                f"Searched in:\n"
                f"  1. {self.assignment_types_dir}/{assignment_type}/{prompt_name}.txt\n"
                f"  2. {self.shared_dir}/{prompt_name}.txt\n"
                f"  3. {self.prompts_base_dir}/{prompt_name}.txt"
            )

        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Apply citation style substitution if provided
        if citation_style:
            normalized_style = self.normalize_citation_style(citation_style)
            content = content.replace('{citation_style}', normalized_style)

        return content

    def get_citation_style_instructions(self, citation_style: str) -> str:
        """
        Get specific instructions for citation style formatting

        Args:
            citation_style: Citation style (APA, MLA, Chicago, Harvard)

        Returns:
            Instructions for the specific citation style
        """
        normalized_style = self.normalize_citation_style(citation_style)

        # Try to load style-specific instructions
        style_file = self.citation_styles_dir / f"{normalized_style.lower()}_instructions.txt"
        if style_file.exists():
            with open(style_file, 'r', encoding='utf-8') as f:
                return f.read()

        # Return default APA instructions if not found
        return self._get_default_apa_instructions()

    def _get_default_apa_instructions(self) -> str:
        """Default APA citation instructions"""
        return """
**APA Citation Format:**
- In-text: (Author, Year) or (Author & Author, Year) or (Author et al., Year)
- Place citations before the period
- No page numbers for general references
- Multiple authors: Use & for two authors, et al. for three or more
"""

    def get_supported_assignment_types(self) -> list[str]:
        """Get list of supported assignment types"""
        return list(set(self.ASSIGNMENT_TYPE_MAP.values()))

    def get_supported_citation_styles(self) -> list[str]:
        """Get list of supported citation styles"""
        return list(set(self.CITATION_STYLE_MAP.values()))


# Global instance for easy access
_prompt_selector = None


def get_prompt_selector() -> PromptSelector:
    """Get singleton PromptSelector instance"""
    global _prompt_selector
    if _prompt_selector is None:
        _prompt_selector = PromptSelector()
    return _prompt_selector
