"""
Test script for reading article abstracts and extracting quotes
"""
import asyncio
from semanticscholar import SemanticScholar

from src.utils.llm_service import get_fast_model


async def test_read_abstracts():
    """Read abstracts from top articles and extract quotes"""

    print("=" * 80)
    print("READING ARTICLE ABSTRACTS")
    print("=" * 80)
    print()

    # Search topic
    topic = "intimate partner violence restorative justice"
    required_sources = 3

    print(f"Topic: {topic}")
    print(f"Required sources: {required_sources}")
    print("-" * 80)

    # Initialize Semantic Scholar
    sch = SemanticScholar()

    # Search for papers
    results = sch.search_paper(topic, limit=10, year="2020-2025")

    # Filter papers with abstracts and sort by citations
    papers_with_abstracts = []
    for paper in results:
        if paper.abstract and len(paper.abstract) > 100:
            papers_with_abstracts.append(paper)

    # Sort by citation count
    papers_with_abstracts.sort(key=lambda x: x.citationCount or 0, reverse=True)

    # Take top N
    selected_papers = papers_with_abstracts[:required_sources]

    print(f"\nSelected {len(selected_papers)} papers with abstracts:\n")

    # Collect abstracts for LLM
    abstracts_text = ""

    for i, paper in enumerate(selected_papers, 1):
        # Format author citation
        if paper.authors:
            if len(paper.authors) == 1:
                author_cite = paper.authors[0].name.split()[-1]
            elif len(paper.authors) == 2:
                author_cite = f"{paper.authors[0].name.split()[-1]} & {paper.authors[1].name.split()[-1]}"
            else:
                author_cite = f"{paper.authors[0].name.split()[-1]} et al."
        else:
            author_cite = "Unknown"

        year = paper.year or "n.d."
        citation = f"({author_cite}, {year})"

        print(f"{i}. {citation}")
        print(f"   Title: {paper.title}")
        print(f"   Citations: {paper.citationCount}")
        print(f"   Abstract: {paper.abstract[:300]}...")
        print()

        # Add to abstracts text for LLM
        abstracts_text += f"""
SOURCE {i}: {citation}
Title: {paper.title}
Abstract: {paper.abstract}

"""

    print("=" * 80)
    print("EXTRACTING QUOTES WITH LLM")
    print("=" * 80)

    # Use LLM to extract relevant quotes
    llm = get_fast_model()

    if not llm:
        print("ERROR: LLM not available")
        return

    prompt = f"""You are an academic writing assistant. Read the following article abstracts and extract 2-3 key quotes or paraphrased ideas from EACH source that would be useful for writing an essay about "{topic}".

For each quote/idea:
1. Write the quote or paraphrased idea
2. Include the in-text citation in APA format

ABSTRACTS:
{abstracts_text}

Extract useful quotes/ideas for each source. Format:

SOURCE 1:
- "Quote or paraphrased idea" (Author, Year)
- "Another quote or idea" (Author, Year)

SOURCE 2:
...
"""

    print("\nAsking LLM to extract quotes...\n")

    response = await llm.ainvoke(prompt)
    print(response.content)


if __name__ == "__main__":
    asyncio.run(test_read_abstracts())
