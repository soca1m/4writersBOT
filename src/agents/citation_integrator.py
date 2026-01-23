"""
Bot 3: Citation Integrator
1. Searches for academic sources via Semantic Scholar Service
2. Inserts citations into the text in APA format (Author, Year)
"""
import logging
import re
from typing import Dict, Any, List

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_fast_model
from src.utils.semantic_scholar import search_papers, Paper

logger = logging.getLogger(__name__)


async def integrate_citations_node(state: OrderWorkflowState) -> dict:
    """
    Bot 3: Searches for sources and inserts citations into text

    Args:
        state: Current workflow state

    Returns:
        Updated state with sources_found and text_with_citations
    """
    logger.info(f"📚 Bot 3: Integrating citations for order {state['order_id']}...")

    draft_text = state.get('draft_text', '')
    requirements = state.get('requirements', {})
    required_sources = requirements.get('required_sources', 3)

    # Handle search_keywords - can be string or list
    search_keywords = requirements.get('search_keywords', requirements.get('main_topic', ''))
    if isinstance(search_keywords, list):
        search_keywords = ' '.join(search_keywords[:3])
    search_keywords = str(search_keywords)[:100]

    if not draft_text:
        logger.error("No text to add citations to")
        return {
            **state,
            "status": "failed",
            "error": "No text for citation integration",
            "agent_logs": state.get('agent_logs', []) + ["[Bot3:Citations] ERROR: No text"]
        }

    print("\n" + "="*80)
    print("📚 Bot 3: SEARCHING FOR ACADEMIC SOURCES...")
    print("="*80 + "\n")

    # Split keywords into separate search queries for better results
    keyword_parts = search_keywords.split()
    search_queries = []

    # Create focused queries (2-3 words each)
    if len(keyword_parts) > 3:
        # Split into chunks of 2-3 words
        for i in range(0, len(keyword_parts), 2):
            query = ' '.join(keyword_parts[i:i+3])
            if len(query) > 5:
                search_queries.append(query)
    else:
        search_queries.append(search_keywords)

    # Also add the main topic as a fallback query
    main_topic = requirements.get('main_topic', '')
    if main_topic and main_topic not in search_queries:
        search_queries.append(main_topic)

    print(f"🔍 Search queries: {search_queries}")
    print(f"   Required sources: {required_sources}")
    print()

    llm = get_fast_model()
    relevant_papers = []

    for query in search_queries:
        if len(relevant_papers) >= required_sources:
            break

        print(f"   Searching: '{query}'...")

        # Search for papers
        papers: List[Paper] = await search_papers(
            query=query,
            limit=required_sources * 3,
            year_min=2020
        )

        if not papers:
            print(f"   No papers found for '{query}'")
            continue

        # Filter: must have abstract
        papers_with_abstract = [p for p in papers if p.abstract and len(p.abstract) > 50]
        print(f"   Found {len(papers_with_abstract)} papers with abstract")

        if not papers_with_abstract:
            continue

        # Check relevance with LLM - use current query, not all keywords
        if llm:
            for p in papers_with_abstract:
                # Skip if we already have this paper
                if any(rp.title == p.title for rp in relevant_papers):
                    continue

                # Check relevance to the current search query (more specific)
                relevance_prompt = f"""Can this paper be cited in an academic essay about "{query}"?

A paper is suitable if it:
- Discusses the topic directly OR
- Provides relevant background/context OR
- Contains related research findings

PAPER TITLE: {p.title}
ABSTRACT: {p.abstract[:500]}

Answer "YES" if suitable for citation, "NO" if completely unrelated."""

                try:
                    response = await llm.ainvoke(relevance_prompt)
                    answer = response.content.strip().upper()
                    if "YES" in answer:
                        relevant_papers.append(p)
                        print(f"   ✓ Relevant: {p.title[:50]}...")
                        if len(relevant_papers) >= required_sources:
                            break
                    else:
                        print(f"   ✗ Not relevant: {p.title[:50]}...")
                except Exception as e:
                    logger.warning(f"Relevance check failed: {e}")
        else:
            # No LLM - use keyword matching
            for p in papers_with_abstract:
                if any(rp.title == p.title for rp in relevant_papers):
                    continue
                topic_words = set(search_keywords.lower().split())
                text = f"{p.title} {p.abstract}".lower()
                if sum(1 for w in topic_words if w in text) >= 2:
                    relevant_papers.append(p)
                    if len(relevant_papers) >= required_sources:
                        break

    papers = relevant_papers

    if not papers:
        print("   ⚠️ No relevant papers found after checking all queries")

    if not papers:
        logger.warning("No papers found from Semantic Scholar")
        print("⚠️ No academic sources found. Proceeding without citations.\n")
        return {
            **state,
            "sources_found": [],
            "text_with_citations": draft_text,
            "citations_inserted": False,
            "status": "citations_added",
            "agent_logs": state.get('agent_logs', []) + ["[Bot3:Citations] No sources found, skipped"]
        }

    # Take only required number of sources
    papers = papers[:required_sources]

    # Convert Paper objects to dicts for state
    sources = [
        {
            "title": p.title,
            "authors": p.authors,
            "year": p.year,
            "abstract": p.abstract,
            "citation": p.citation,
            "url": p.url,
            "citation_count": p.citation_count
        }
        for p in papers
    ]

    print(f"✅ Found {len(sources)} academic sources:\n")
    for i, source in enumerate(sources, 1):
        print(f"   {i}. {source['citation']}")
        print(f"      {source['title'][:60]}...")
        print(f"      Citations: {source['citation_count']}")
        print()

    # Insert citations using LLM
    print("📝 Inserting citations into text...")

    llm = get_fast_model()
    if not llm:
        logger.warning("LLM not available for citation insertion")
        return {
            **state,
            "sources_found": sources,
            "text_with_citations": draft_text,
            "citations_inserted": False,
            "status": "citations_added",
            "agent_logs": state.get('agent_logs', []) + ["[Bot3:Citations] LLM unavailable"]
        }

    sources_info = "\n".join([
        f"SOURCE {i}: {s['citation']}\n  Title: {s['title']}\n  Abstract: {s['abstract'][:200] if s['abstract'] else 'No abstract'}..."
        for i, s in enumerate(sources, 1)
    ])

    citation_prompt = f"""Insert academic citations into this text. Use the provided sources.

TEXT TO ADD CITATIONS TO:
{draft_text}

AVAILABLE SOURCES:
{sources_info}

CITATION RULES:
1. Insert citations in APA format: (Author, Year) or (Author & Author, Year) or (Author et al., Year)
2. Place citations at the END of sentences that make claims or present facts
3. Each source should be cited at least once
4. Citations go BEFORE the period: "...this is true (Smith, 2023)."
5. DO NOT add a References section
6. Keep ALL original text - only ADD citations

EXAMPLES:
- "Research shows that exercise improves health (Johnson, 2022)."
- "According to recent studies (Brown & Davis, 2021), stress affects performance."

Return the COMPLETE text with citations inserted. Do not change the content, only add citations."""

    try:
        response = await llm.ainvoke(citation_prompt)
        text_with_citations = response.content.strip()

        # Remove any References section if added
        for marker in ["References", "Bibliography", "Works Cited"]:
            if marker in text_with_citations:
                text_with_citations = text_with_citations[:text_with_citations.find(marker)].strip()

        # Count citations inserted
        citation_pattern = r'\([A-Z][a-z]+(?:\s+(?:&|et al\.))?,?\s*\d{4}\)'
        citations_found = len(re.findall(citation_pattern, text_with_citations))

        print(f"\n✅ Citations inserted: {citations_found}")
        print()

        logger.info(f"Inserted {citations_found} citations from {len(sources)} sources")

        return {
            **state,
            "sources_found": sources,
            "text_with_citations": text_with_citations,
            "citations_inserted": True,
            "status": "citations_added",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot3:Citations] Added {citations_found} citations from {len(sources)} sources"
            ]
        }

    except Exception as e:
        logger.error(f"Error inserting citations: {e}")
        return {
            **state,
            "sources_found": sources,
            "text_with_citations": draft_text,
            "citations_inserted": False,
            "status": "citations_added",
            "agent_logs": state.get('agent_logs', []) + [f"[Bot3:Citations] ERROR: {str(e)}"]
        }
