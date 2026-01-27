"""
Text format conversion utilities

Purpose:
- JSON structure is used internally throughout the pipeline (Writer → Citation Integrator → Quality Checker → Reviser)
- Markdown is only generated at the END for user display
"""
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def json_to_markdown(json_structure: Dict[str, Any]) -> str:
    """
    Convert JSON essay structure to markdown format for final user display

    Used at the END of the pipeline to convert internal JSON structure to user-friendly markdown.

    Args:
        json_structure: Dict with 'sections' array containing essay structure

    Returns:
        Markdown formatted text

    Example:
        >>> structure = {
        ...     "sections": [
        ...         {"type": "introduction", "heading": "Introduction", "paragraphs": ["Text..."]},
        ...         {"type": "body", "heading": "Main Points", "paragraphs": ["Para 1", "Para 2"]},
        ...         {"type": "conclusion", "heading": "Conclusion", "paragraphs": ["Text..."]}
        ...     ]
        ... }
        >>> markdown = json_to_markdown(structure)
        ## Introduction

        Text...

        ## Main Points

        Para 1

        Para 2

        ## Conclusion

        Text...
    """
    sections = json_structure.get('sections', [])
    markdown_parts = []

    for section in sections:
        heading = section.get('heading', '')
        paragraphs = section.get('paragraphs', [])

        # Add heading
        if heading:
            markdown_parts.append(f"## {heading}")
            markdown_parts.append("")  # Empty line after heading

        # Add paragraphs
        for paragraph in paragraphs:
            markdown_parts.append(paragraph)
            markdown_parts.append("")  # Empty line after paragraph

    # Join with newlines, remove trailing empty lines
    markdown = "\n".join(markdown_parts).rstrip()

    return markdown


def markdown_to_json(markdown_text: str) -> Dict[str, Any]:
    """
    Convert markdown essay to JSON structure

    Args:
        markdown_text: Markdown formatted essay

    Returns:
        Dict with 'sections' array

    Note: This is best-effort parsing and may not perfectly identify all sections
    """
    lines = markdown_text.split('\n')
    sections = []
    current_section = None
    current_paragraph_lines = []

    for line in lines:
        # Check if heading
        if line.startswith('## '):
            # Save previous section if exists
            if current_section and current_paragraph_lines:
                paragraph = ' '.join(current_paragraph_lines).strip()
                if paragraph:
                    current_section['paragraphs'].append(paragraph)
                current_paragraph_lines = []

            if current_section:
                sections.append(current_section)

            # Start new section
            heading = line[3:].strip()
            section_type = "body"  # Default

            if "introduction" in heading.lower():
                section_type = "introduction"
            elif "conclusion" in heading.lower():
                section_type = "conclusion"

            current_section = {
                "type": section_type,
                "heading": heading,
                "paragraphs": []
            }

        elif line.strip():
            # Non-empty line - part of paragraph
            current_paragraph_lines.append(line.strip())

        else:
            # Empty line - end of paragraph
            if current_paragraph_lines:
                paragraph = ' '.join(current_paragraph_lines).strip()
                if current_section:
                    current_section['paragraphs'].append(paragraph)
                current_paragraph_lines = []

    # Save last section
    if current_section:
        if current_paragraph_lines:
            paragraph = ' '.join(current_paragraph_lines).strip()
            if paragraph:
                current_section['paragraphs'].append(paragraph)
        sections.append(current_section)

    return {"sections": sections}
