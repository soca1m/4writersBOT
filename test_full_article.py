"""
Test script for fetching full article text by DOI
"""
import asyncio
import httpx
from io import BytesIO

# Для чтения PDF
try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False


async def get_open_access_url(doi: str, email: str = "test@example.com") -> dict:
    """
    Get open access URL for article via Unpaywall API

    Args:
        doi: DOI of the article
        email: Email for API (required by Unpaywall)

    Returns:
        dict with URLs and metadata
    """
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}


async def download_pdf(pdf_url: str) -> bytes | None:
    """Download PDF from URL"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(pdf_url, headers=headers)

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type or pdf_url.endswith('.pdf'):
                return response.content

        return None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes"""

    if not HAS_PYPDF2:
        return "PyPDF2 not installed"

    reader = PdfReader(BytesIO(pdf_bytes))
    text = ""

    for page in reader.pages:
        text += page.extract_text() + "\n"

    return text


async def test_fetch_full_article():
    """Test fetching full article by DOI"""

    print("=" * 80)
    print("FETCHING FULL ARTICLE BY DOI")
    print("=" * 80)
    print()

    # Test DOIs from our Semantic Scholar search
    test_dois = [
        "10.1016/j.ssmmh.2022.100085",  # Open access article about IPV and RJ
        "10.3390/LAWS10010013",          # MDPI article (usually open access)
        "10.1177/10443894231212546",     # SAGE article
    ]

    for doi in test_dois:
        print(f"\n{'='*80}")
        print(f"DOI: {doi}")
        print(f"{'='*80}")

        # Step 1: Get open access info from Unpaywall
        print("\n1. Checking Unpaywall for open access version...")
        result = await get_open_access_url(doi)

        if "error" in result:
            print(f"   Error: {result['error']}")
            continue

        print(f"   Title: {result.get('title', 'N/A')[:60]}...")
        print(f"   Is Open Access: {result.get('is_oa', False)}")

        # Get best OA location
        oa_location = result.get('best_oa_location')

        if not oa_location:
            print("   No open access version found")
            continue

        pdf_url = oa_location.get('url_for_pdf') or oa_location.get('url')
        print(f"   PDF URL: {pdf_url}")
        print(f"   License: {oa_location.get('license', 'N/A')}")

        if not pdf_url:
            print("   No PDF URL available")
            continue

        # Step 2: Download PDF
        print("\n2. Downloading PDF...")
        pdf_bytes = await download_pdf(pdf_url)

        if not pdf_bytes:
            print("   Failed to download PDF")
            continue

        print(f"   Downloaded: {len(pdf_bytes)} bytes")

        # Step 3: Extract text
        print("\n3. Extracting text from PDF...")
        text = extract_text_from_pdf(pdf_bytes)

        if text:
            print(f"   Extracted: {len(text)} characters")
            print(f"\n   First 500 characters:")
            print("-" * 40)
            print(text[:500])
            print("-" * 40)

            # Word count
            words = len(text.split())
            print(f"\n   Total words: {words}")
        else:
            print("   Failed to extract text")

        # Only test first successful one
        break

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_fetch_full_article())
