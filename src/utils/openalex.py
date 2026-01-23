"""
OpenAlex API Service
Free academic paper search without rate limits
https://docs.openalex.org/
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Academic paper from OpenAlex"""
    paper_id: str
    title: str
    authors: str
    year: int
    abstract: str
    citation: str  # APA in-text citation format
    url: str
    citation_count: int


class OpenAlexService:
    """
    Service for searching academic papers via OpenAlex API

    Features:
    - No rate limits
    - Free and open
    - Large academic database
    """

    BASE_URL = "https://api.openalex.org"
    DEFAULT_TIMEOUT = 15.0

    def __init__(self, email: str = "academic-bot@example.com", timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize the service

        Args:
            email: Email for polite pool (faster responses)
            timeout: Request timeout in seconds
        """
        self.email = email
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": f"Academic Research Bot (mailto:{self.email})"}
            )
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _format_apa_citation(self, authorships: List[Dict], year: int) -> tuple[str, str]:
        """Format authors for APA citation"""
        if not authorships:
            return "Unknown", f"(Unknown, {year})"

        # Extract author names
        names = []
        for a in authorships:
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

    async def search(
        self,
        query: str,
        limit: int = 5,
        year_min: Optional[int] = 2020,
        year_max: Optional[int] = None
    ) -> List[Paper]:
        """
        Search for academic papers

        Args:
            query: Search query string
            limit: Maximum results (max 200)
            year_min: Minimum publication year (default 2020)
            year_max: Maximum publication year

        Returns:
            List of Paper objects
        """
        query = query.strip()
        if not query:
            return []

        logger.info(f"OpenAlex search: '{query}' (limit={limit}, year_min={year_min})")

        params = {
            "search": query,
            "per_page": min(limit, 200),
            "select": "id,title,authorships,publication_year,cited_by_count,doi,abstract_inverted_index"
        }

        # Build filters
        filters = []
        if year_min:
            filters.append(f"publication_year:>{year_min - 1}")
        if year_max:
            filters.append(f"publication_year:<{year_max + 1}")

        if filters:
            params["filter"] = ",".join(filters)

        # Sort by citations
        params["sort"] = "cited_by_count:desc"

        client = await self._get_client()

        try:
            response = await client.get(f"{self.BASE_URL}/works", params=params)
            response.raise_for_status()
            data = response.json()

            papers = []
            for item in data.get("results", []):
                title = item.get("title")
                year = item.get("publication_year")

                if not title or not year:
                    continue

                authorships = item.get("authorships", [])
                author_str, citation = self._format_apa_citation(authorships, year)

                # Reconstruct abstract from inverted index
                abstract = ""
                abstract_idx = item.get("abstract_inverted_index")
                if abstract_idx:
                    try:
                        # Reconstruct abstract from inverted index
                        words = {}
                        for word, positions in abstract_idx.items():
                            for pos in positions:
                                words[pos] = word
                        abstract = " ".join([words[i] for i in sorted(words.keys())])
                    except:
                        pass

                # Build URL
                openalex_id = item.get("id", "")
                doi = item.get("doi", "")
                url = doi if doi else openalex_id

                papers.append(Paper(
                    paper_id=openalex_id,
                    title=title,
                    authors=author_str,
                    year=year,
                    abstract=abstract[:500] if abstract else "",
                    citation=citation,
                    url=url,
                    citation_count=item.get("cited_by_count") or 0
                ))

            logger.info(f"OpenAlex found {len(papers)} papers")
            return papers

        except httpx.TimeoutException:
            logger.warning("OpenAlex request timeout")
            return []

        except Exception as e:
            logger.error(f"OpenAlex error: {e}")
            return []


# Singleton
_service: Optional[OpenAlexService] = None


def get_openalex_service() -> OpenAlexService:
    global _service
    if _service is None:
        _service = OpenAlexService()
    return _service


async def search_papers(
    query: str,
    limit: int = 5,
    year_min: Optional[int] = 2020,
    year_max: Optional[int] = None
) -> List[Paper]:
    """Search for papers via OpenAlex"""
    service = get_openalex_service()
    return await service.search(query, limit=limit, year_min=year_min, year_max=year_max)
