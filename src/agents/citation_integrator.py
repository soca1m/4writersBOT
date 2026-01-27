"""
Bot 3: Citation Integrator
1. Searches for academic sources via Semantic Scholar Service
2. Inserts citations into the text in APA format (Author, Year)
"""
import logging
import re
import json
from typing import Dict, Any, List

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_smart_model
from src.utils.semantic_scholar import search_papers, Paper
from src.services.prompt_manager import PromptManager

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
    citation_action = state.get('citation_action', 'keep')

    # Check if we already have sources in state
    existing_sources = state.get('sources_found', [])

    if not draft_text:
        logger.error("No text to add citations to")
        return {
            **state,
            "status": "failed",
            "error": "No text for citation integration",
            "agent_logs": state.get('agent_logs', []) + ["[Bot3:Citations] ERROR: No text"]
        }

    # Determine if we need to search for new sources
    need_new_search = (
        not existing_sources or  # No sources yet
        len(existing_sources) < required_sources or  # Not enough sources
        citation_action == 'reinsert'  # Quality checker requests new search
    )

    sources = existing_sources  # Use existing sources by default

    if need_new_search:
        print("\n" + "="*80)
        print("📚 Bot 3: SEARCHING FOR ACADEMIC SOURCES...")
        print("="*80 + "\n")

        # Get main topic for context
        main_topic = requirements.get('main_topic', '')

        # Use researcher to generate smart search queries
        from src.agents.researcher import generate_search_queries

        search_queries = await generate_search_queries(
            main_topic=main_topic,
            required_sources=required_sources,
            llm=get_smart_model()
        )

        if not search_queries:
            # Fallback: use search_keywords if researcher fails
            search_keywords = requirements.get('search_keywords', main_topic)
            if isinstance(search_keywords, list):
                search_queries = search_keywords[:3]
            else:
                search_queries = [search_keywords]

        print(f"🔍 Search queries: {search_queries}")
        print(f"   Required sources: {required_sources}")
        print()

        llm = get_smart_model()
        relevant_papers = []

        for query in search_queries:
            if len(relevant_papers) >= required_sources:
                break

            print(f"   Searching: '{query}'...")

            # Search for papers (request more to have better selection)
            papers: List[Paper] = await search_papers(
                query=query,
                limit=max(required_sources * 10, 20),  # Request 10x sources or min 20
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

            # Check relevance with LLM - compare to main topic for accuracy
            if llm:
                for p in papers_with_abstract:
                    # Skip if we already have this paper
                    if any(rp.title == p.title for rp in relevant_papers):
                        continue

                    # Check relevance to the MAIN TOPIC (not just the search query)
                    relevance_prompt = f"""You are evaluating if this academic paper is relevant for citing in an essay.

ESSAY TOPIC: {main_topic}

PAPER TO EVALUATE:
Title: {p.title}
Abstract: {p.abstract}

RELEVANCE CRITERIA:
✓ RELEVANT if paper:
- Discusses the essay topic or closely related concepts
- Provides background, context, data, or analysis relevant to the topic
- Contains research findings or theories applicable to the topic

✗ NOT RELEVANT if paper:
- Is about a completely unrelated topic or field
- Focuses exclusively on technical/clinical details when topic is about policy/social issues

Answer ONLY "YES" (relevant) or "NO" (not relevant)."""

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
            print("   🔄 Trying OpenAlex directly...")
            print()

            # Try OpenAlex directly with simpler queries
            from src.utils.semantic_scholar import AcademicSearchService
            search_service = AcademicSearchService()

            # Try with simplified topic (first 4-5 words)
            simple_query = ' '.join(main_topic.split()[:5])

            openalex_papers = await search_service._search_openalex(
                query=simple_query,
                limit=max(required_sources * 10, 20),  # Request more papers
                year_min=2020
            )

            if openalex_papers:
                print(f"   Found {len(openalex_papers)} papers from OpenAlex")

                # Check relevance with LLM
                if llm:
                    for p in openalex_papers:
                        if not p.abstract or len(p.abstract) < 50:
                            continue

                        relevance_prompt = f"""You are evaluating if this academic paper is relevant for citing in an essay.

ESSAY TOPIC: {main_topic}

PAPER TO EVALUATE:
Title: {p.title}
Abstract: {p.abstract}

RELEVANCE CRITERIA:
✓ RELEVANT if paper:
- Discusses the essay topic or closely related concepts
- Provides background, context, data, or analysis relevant to the topic
- Contains research findings or theories applicable to the topic

✗ NOT RELEVANT if paper:
- Is about a completely unrelated topic or field
- Focuses exclusively on technical/clinical details when topic is about policy/social issues

Answer ONLY "YES" (relevant) or "NO" (not relevant)."""

                        try:
                            response = await llm.ainvoke(relevance_prompt)
                            answer = response.content.strip().upper()
                            if "YES" in answer:
                                papers.append(p)
                                print(f"   ✓ Relevant: {p.title[:50]}...")
                                if len(papers) >= required_sources:
                                    break
                            else:
                                print(f"   ✗ Not relevant: {p.title[:50]}...")
                        except Exception as e:
                            logger.warning(f"Relevance check failed: {e}")
                else:
                    papers = openalex_papers[:required_sources]

        if not papers:
            logger.warning("No papers found from any source")
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
    else:
        print("\n" + "="*80)
        print("📚 Bot 3: REUSING EXISTING SOURCES...")
        print("="*80 + "\n")

        print(f"✅ Using {len(sources)} previously found sources:\n")
        for i, source in enumerate(sources, 1):
            print(f"   {i}. {source['citation']}")
            print(f"      {source['title'][:60]}...")
            print()

    # Insert citations using LLM
    print("📝 Inserting citations into text...")

    llm = get_smart_model()
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
        f"SOURCE {i}: {s['citation']}\n  Title: {s['title']}\n  Abstract: {s['abstract'] if s['abstract'] else 'No abstract'}"
        for i, s in enumerate(sources, 1)
    ])

    # Load prompt from file with assignment-type support
    requirements = state.get('requirements', {})
    assignment_type = requirements.get('assignment_type', 'essay')
    citation_style = requirements.get('citation_style', 'APA')

    prompt_template = PromptManager.load(
        "citation_integrator_prompt",
        assignment_type=assignment_type,
        citation_style=citation_style
    )

    # Format prompt with variables
    citation_prompt = PromptManager.format(
        prompt_template,
        draft_text=draft_text,
        sources_info=sources_info,
        citation_style=citation_style
    )

    try:
        response = await llm.ainvoke(citation_prompt)
        response_text = response.content.strip()

        # Remove any References section if added
        text_with_citations = response_text
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
