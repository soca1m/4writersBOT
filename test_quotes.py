"""
Simple test: search articles, get abstracts, extract quotes
"""
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

from semanticscholar import SemanticScholar
from src.utils.llm_service import get_fast_model


async def main():
    topic = "intimate partner violence restorative justice"
    print(f"Topic: {topic}\n")

    # 1. Search articles
    print("1. Searching Semantic Scholar...")
    sch = SemanticScholar()
    results = sch.search_paper(topic, limit=5, year="2020-2025")

    # 2. Get papers with abstracts
    papers = []
    for paper in results:
        if paper.abstract and len(paper.abstract) > 100:
            # Format citation
            if paper.authors:
                if len(paper.authors) == 1:
                    author = paper.authors[0].name.split()[-1]
                elif len(paper.authors) == 2:
                    author = f"{paper.authors[0].name.split()[-1]} & {paper.authors[1].name.split()[-1]}"
                else:
                    author = f"{paper.authors[0].name.split()[-1]} et al."
            else:
                author = "Unknown"

            papers.append({
                'title': paper.title,
                'citation': f"({author}, {paper.year})",
                'abstract': paper.abstract
            })

            if len(papers) >= 3:
                break

    print(f"   Found {len(papers)} papers with abstracts\n")

    # 3. Show papers
    for i, p in enumerate(papers, 1):
        print(f"{i}. {p['citation']}")
        print(f"   {p['title'][:60]}...")
        print()

    # 4. Extract quotes with LLM
    print("2. Extracting quotes with gpt-5-mini...")

    abstracts_text = ""
    for i, p in enumerate(papers, 1):
        abstracts_text += f"SOURCE {i} {p['citation']}:\n{p['abstract']}\n\n"

    llm = get_fast_model()
    prompt = f"""Extract 1-2 key ideas from each source that can be used in an essay about "{topic}".
Paraphrase (don't copy). Be specific.

{abstracts_text}

Format:
SOURCE 1:
- [idea]
SOURCE 2:
- [idea]
etc."""

    response = await llm.ainvoke(prompt)

    print("\n3. Extracted quotes:\n")
    print(response.content)


if __name__ == "__main__":
    asyncio.run(main())
