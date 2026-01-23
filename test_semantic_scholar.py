"""
Test script for Semantic Scholar Service
"""
import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.semantic_scholar import SemanticScholarService, search_papers


async def test_service():
    """Test the SemanticScholarService"""
    print("=" * 60)
    print("SEMANTIC SCHOLAR SERVICE TEST")
    print("=" * 60)

    service = SemanticScholarService(timeout=20.0)

    queries = [
        "gender symmetry domestic violence",
        "restorative justice",
        "machine learning healthcare",
    ]

    for query in queries:
        print(f"\n🔍 Query: {query}")
        try:
            papers = await service.search(query, limit=3)

            if papers:
                print(f"   ✅ Found {len(papers)} papers:")
                for i, paper in enumerate(papers, 1):
                    print(f"   {i}. {paper.citation}")
                    print(f"      {paper.title[:55]}...")
                    print(f"      Citations: {paper.citation_count}")
            else:
                print("   ⚠️ No papers found")

        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}: {e}")

        # Small delay between requests to avoid rate limiting
        await asyncio.sleep(1)

    await service.close()


async def test_with_year_filter():
    """Test with year filter"""
    print("\n" + "=" * 60)
    print("TEST WITH YEAR FILTER (2020+)")
    print("=" * 60)

    service = SemanticScholarService()

    query = "domestic violence"
    print(f"\n🔍 Query: {query} (year >= 2020)")

    try:
        papers = await service.search(query, limit=3, year_min=2020)

        if papers:
            print(f"   ✅ Found {len(papers)} papers:")
            for paper in papers:
                print(f"   • {paper.citation} - {paper.title[:40]}...")
        else:
            print("   ⚠️ No papers found")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    await service.close()


async def test_convenience_function():
    """Test the convenience function"""
    print("\n" + "=" * 60)
    print("TEST CONVENIENCE FUNCTION")
    print("=" * 60)

    query = "criminal justice reform"
    print(f"\n🔍 Query: {query}")

    try:
        papers = await search_papers(query, limit=2, year_min=2018)

        if papers:
            print(f"   ✅ Found {len(papers)} papers:")
            for paper in papers:
                print(f"   • {paper.citation}")
                print(f"     {paper.title[:50]}...")
                if paper.abstract:
                    print(f"     Abstract: {paper.abstract[:100]}...")
        else:
            print("   ⚠️ No papers found")

    except Exception as e:
        print(f"   ❌ Error: {e}")


async def main():
    print("\n🧪 SEMANTIC SCHOLAR SERVICE TEST\n")

    await test_service()
    await test_with_year_filter()
    await test_convenience_function()

    print("\n" + "=" * 60)
    print("✅ Tests complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
