"""
Research Query Generator
Generates smart search queries for academic databases based on assignment topic
"""
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Load researcher prompt
RESEARCHER_PROMPT_FILE = Path(__file__).parent.parent.parent / 'prompts' / 'researcher_prompt.txt'


async def generate_search_queries(
    main_topic: str,
    required_sources: int = 2,
    llm = None
) -> List[str]:
    """
    Generate smart search queries for academic databases

    Args:
        main_topic: The main topic/question for the assignment
        required_sources: Number of sources needed (affects number of queries)
        llm: Language model instance

    Returns:
        List of 3-5 focused search queries
    """
    if not llm:
        # Fallback: simple keyword extraction
        logger.warning("No LLM available for query generation, using simple fallback")
        return [main_topic[:80]]

    if not RESEARCHER_PROMPT_FILE.exists():
        logger.error(f"Researcher prompt file not found: {RESEARCHER_PROMPT_FILE}")
        return [main_topic[:80]]

    try:
        # Load prompt template
        prompt_template = RESEARCHER_PROMPT_FILE.read_text(encoding='utf-8')

        # Fill in parameters
        prompt = prompt_template.replace('{main_topic}', main_topic)
        prompt = prompt.replace('{required_sources}', str(required_sources))
        prompt = prompt.replace('{min_year}', '2020')

        # Get response from LLM
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()

        # Parse queries from response (expected format: numbered list)
        queries = []
        for line in response_text.split('\n'):
            line = line.strip()
            # Remove numbering (1. 2. etc)
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering and quotes
                query = line.lstrip('0123456789.-) ').strip('"\'')
                if len(query) > 5:  # Minimum query length
                    queries.append(query)

        if queries:
            logger.info(f"Generated {len(queries)} search queries from researcher")
            return queries[:5]  # Max 5 queries
        else:
            logger.warning("Failed to parse queries from researcher response, using fallback")
            return [main_topic[:80]]

    except Exception as e:
        logger.error(f"Error generating search queries: {e}")
        return [main_topic[:80]]
