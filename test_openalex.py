"""
Test script for OpenAlex API - free academic paper search
https://docs.openalex.org/
"""
import asyncio
import httpx


async def search_openalex(query: str, limit: int = 5, year_min: int = None) -> list:
    """
    Search OpenAlex API

    Args:
        query: Search query
        limit: Max results
        year_min: Minimum publication year

    Returns:
        List of papers
    """
    url = "https://api.openalex.org/works"

    params = {
        "search": query,
        "per_page": limit,
        "select": "id,title,authorships,publication_year,cited_by_count,doi"
    }

    if year_min:
        params["filter"] = f"publication_year:>{year_min - 1}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            url,
            params=params,
            headers={"User-Agent": "Academic Research Bot (mailto:test@example.com)"}
        )
        response.raise_for_status()
        return response.json().get("results", [])


def format_apa_citation(authors: list, year: int) -> tuple:
    """Format authors for APA citation"""
    if not authors:
        return "Unknown", f"(Unknown, {year})"

    # Extract author names
    names = []
    for a in authors:
        author_info = a.get("author", {})
        name = author_info.get("display_name", "")
        if name:
            names.append(name)

    if not names:
        return "Unknown", f"(Unknown, {year})"

    if len(names) == 1:
        last = names[0].split()[-1]
        return names[0], f"({last}, {year})"
    elif len(names) == 2:
        lasts = [n.split()[-1] for n in names]
        return " & ".join(names), f"({' & '.join(lasts)}, {year})"
    else:
        last = names[0].split()[-1]
        return f"{names[0]} et al.", f"({last} et al., {year})"


async def test_openalex():
    """Test OpenAlex API"""
    print("=" * 60)
    print("OPENALEX API TEST")
    print("=" * 60)

    queries = [
        "gender symmetry domestic violence",
        "restorative justice",
        "machine learning healthcare",
    ]

    for query in queries:
        print(f"\n🔍 Query: {query}")
        try:
            papers = await search_openalex(query, limit=3, year_min=2020)

            if papers:
                print(f"   ✅ Found {len(papers)} papers:")
                for i, paper in enumerate(papers, 1):
                    title = paper.get("title", "No title")
                    year = paper.get("publication_year", 0)
                    citations = paper.get("cited_by_count", 0)
                    authors = paper.get("authorships", [])

                    author_str, citation = format_apa_citation(authors, year)

                    print(f"   {i}. {citation}")
                    print(f"      {title[:55]}...")
                    print(f"      Citations: {citations}")
            else:
                print("   ⚠️ No papers found")

        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}: {e}")


async def test_rate_limits():
    """Test that there are no rate limits"""
    print("\n" + "=" * 60)
    print("RATE LIMIT TEST (10 rapid requests)")
    print("=" * 60)

    queries = ["psychology", "sociology", "economics", "biology", "chemistry",
               "physics", "medicine", "law", "education", "history"]

    success = 0
    for i, query in enumerate(queries, 1):
        try:
            papers = await search_openalex(query, limit=1)
            if papers:
                success += 1
                print(f"   {i}. ✅ {query}: found {len(papers)} paper(s)")
            else:
                print(f"   {i}. ⚠️ {query}: no results")
        except Exception as e:
            print(f"   {i}. ❌ {query}: {e}")

    print(f"\n   Success rate: {success}/10")


async def main():
    print("\n🧪 OPENALEX API TEST\n")

    await test_openalex()
    await test_rate_limits()

    print("\n" + "=" * 60)
    print("✅ Tests complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
