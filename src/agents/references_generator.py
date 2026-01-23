"""
Bot 7: References Generator
Generates APA format References section from sources_found
Adds it to the end of final_text
"""
import logging
from typing import Dict, Any, List

from src.workflows.state import OrderWorkflowState

logger = logging.getLogger(__name__)


def format_apa_reference(source: Dict[str, Any]) -> str:
    """
    Format a single source as APA reference

    Args:
        source: Source dict with title, authors, year, url

    Returns:
        APA formatted reference string
    """
    authors = source.get('authors', 'Unknown')
    year = source.get('year', 'n.d.')
    title = source.get('title', 'Untitled')
    url = source.get('url', '')

    # Format authors for APA (Last, F. M.)
    # The source already has formatted authors from Semantic Scholar
    if ' et al.' in authors:
        # Keep et al. format
        author_part = authors
    elif ' & ' in authors:
        # Multiple authors already formatted
        author_part = authors
    else:
        # Single author - try to format as Last, F. M.
        parts = authors.split()
        if len(parts) >= 2:
            last = parts[-1]
            initials = ". ".join([p[0] for p in parts[:-1]]) + "."
            author_part = f"{last}, {initials}"
        else:
            author_part = authors

    # Build reference
    reference = f"{author_part} ({year}). {title}."

    if url:
        reference += f" Retrieved from {url}"

    return reference


async def generate_references_node(state: OrderWorkflowState) -> dict:
    """
    Bot 7: Generates References section and creates final text

    Args:
        state: Current workflow state

    Returns:
        Updated state with references and final_text
    """
    logger.info(f"📚 Bot 7: Generating references for order {state['order_id']}...")

    text = state.get('text_with_citations', state.get('draft_text', ''))
    sources = state.get('sources_found', [])

    if not text:
        logger.error("No text to add references to")
        return {
            **state,
            "status": "failed",
            "error": "No text for references generation",
            "agent_logs": state.get('agent_logs', []) + ["[Bot7:References] ERROR: No text"]
        }

    print("\n" + "="*80)
    print("📚 Bot 7: GENERATING REFERENCES")
    print("="*80 + "\n")

    # Generate References section
    if sources:
        references_lines = ["References", ""]

        # Sort sources alphabetically by author
        sorted_sources = sorted(sources, key=lambda x: x.get('authors', 'Unknown'))

        for source in sorted_sources:
            ref = format_apa_reference(source)
            references_lines.append(ref)
            print(f"   • {ref[:70]}...")

        references = "\n".join(references_lines)
        print(f"\n   Generated {len(sources)} references\n")
    else:
        references = ""
        print("   ⚠️ No sources to generate references from\n")

    # Combine text with references
    if references:
        final_text = f"{text}\n\n{references}"
    else:
        final_text = text

    # Count final words
    word_count = len(final_text.split())

    print("="*80)
    print("✅ WORKFLOW COMPLETED")
    print("="*80)
    print(f"\n   Final word count: {word_count}")
    print(f"   Sources cited: {len(sources)}")
    print(f"   Status: completed\n")

    logger.info(f"References generated, final text: {word_count} words")

    return {
        **state,
        "references": references,
        "final_text": final_text,
        "word_count": word_count,
        "status": "completed",
        "agent_logs": state.get('agent_logs', []) + [
            f"[Bot7:References] Generated {len(sources)} references, final: {word_count} words"
        ]
    }
