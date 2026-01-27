"""
JSON parsing utilities for LLM responses
"""
import json
import re
from typing import Dict, Any


def parse_json_response(text: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from LLM response

    Handles common LLM response formats:
    - Pure JSON
    - JSON wrapped in markdown code blocks
    - JSON with extra text before/after

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict, or empty dict if parsing fails

    Example:
        >>> response = "```json\\n{\"key\": \"value\"}\\n```"
        >>> parse_json_response(response)
        {'key': 'value'}
    """
    if not text:
        return {}

    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # Try direct parsing first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}
