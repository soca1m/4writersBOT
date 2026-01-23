"""
Academic Paper Search Service
Primary: Semantic Scholar API
Fallback: OpenAlex API (no rate limits)
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Academic paper"""
    paper_id: str
    title: str
    authors: str
    year: int
    abstract: str
    citation: str  # APA in-text citation format
    url: str
    citation_count: int


class AcademicSearchService:
    """
    Service for searching academic papers

    Primary: Semantic Scholar (better relevance)
    Fallback: OpenAlex (no rate limits)
    """

    SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1"
    OPENALEX_URL = "https://api.openalex.org"

    DEFAULT_TIMEOUT = 15.0
    RETRY_DELAY = 3.0
    MAX_RETRIES = 2

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0 Academic Research Bot"}
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _format_apa_citation(self, authors: List, year: int, source: str = "semantic") -> tuple[str, str]:
        """Format authors for APA citation"""
        if not authors:
            return "Unknown", f"(Unknown, {year})"

        # Extract names based on source format
        names = []
        for a in authors:
            if source == "semantic":
                name = a.get("name", "")
            else:  # openalex
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

    async def _search_semantic_scholar(
        self,
        query: str,
        limit: int,
        year_min: Optional[int]
    ) -> List[Paper]:
        """Search Semantic Scholar API"""
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": "title,authors,year,abstract,citationCount,url"
        }

        if year_min:
            params["year"] = f"{year_min}-"

        client = await self._get_client()

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.get(
                    f"{self.SEMANTIC_SCHOLAR_URL}/paper/search",
                    params=params
                )

                if response.status_code == 429:
                    wait = float(response.headers.get("Retry-After", self.RETRY_DELAY))
                    logger.warning(f"Semantic Scholar rate limited, waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()

                papers = []
                for item in data.get("data", []):
                    title = item.get("title")
                    year = item.get("year")

                    if not title or not year:
                        continue

                    authors = item.get("authors", [])
                    author_str, citation = self._format_apa_citation(authors, year, "semantic")

                    papers.append(Paper(
                        paper_id=item.get("paperId", ""),
                        title=title,
                        authors=author_str,
                        year=year,
                        abstract=item.get("abstract") or "",
                        citation=citation,
                        url=item.get("url") or "",
                        citation_count=item.get("citationCount") or 0
                    ))

                papers.sort(key=lambda p: p.citation_count, reverse=True)
                return papers

            except httpx.TimeoutException:
                logger.warning(f"Semantic Scholar timeout (attempt {attempt + 1})")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    continue
                logger.error(f"Semantic Scholar HTTP error: {e.response.status_code}")
                break
            except Exception as e:
                logger.error(f"Semantic Scholar error: {e}")
                break

        return []

    async def _search_openalex(
        self,
        query: str,
        limit: int,
        year_min: Optional[int]
    ) -> List[Paper]:
        """Search OpenAlex API (fallback)"""
        params = {
            "search": query,
            "per_page": min(limit, 200),
            "select": "id,title,authorships,publication_year,cited_by_count,doi,abstract_inverted_index",
            "sort": "cited_by_count:desc"
        }

        if year_min:
            params["filter"] = f"publication_year:>{year_min - 1}"

        client = await self._get_client()

        try:
            response = await client.get(f"{self.OPENALEX_URL}/works", params=params)
            response.raise_for_status()
            data = response.json()

            papers = []
            for item in data.get("results", []):
                title = item.get("title")
                year = item.get("publication_year")

                if not title or not year:
                    continue

                authorships = item.get("authorships", [])
                author_str, citation = self._format_apa_citation(authorships, year, "openalex")

                # Reconstruct abstract
                abstract = ""
                abstract_idx = item.get("abstract_inverted_index")
                if abstract_idx:
                    try:
                        words = {}
                        for word, positions in abstract_idx.items():
                            for pos in positions:
                                words[pos] = word
                        abstract = " ".join([words[i] for i in sorted(words.keys())])
                    except:
                        pass

                doi = item.get("doi", "")
                url = doi if doi else item.get("id", "")

                papers.append(Paper(
                    paper_id=item.get("id", ""),
                    title=title,
                    authors=author_str,
                    year=year,
                    abstract=abstract[:500] if abstract else "",
                    citation=citation,
                    url=url,
                    citation_count=item.get("cited_by_count") or 0
                ))

            return papers

        except Exception as e:
            logger.error(f"OpenAlex error: {e}")
            return []

    async def search(
        self,
        query: str,
        limit: int = 5,
        year_min: Optional[int] = 2020
    ) -> List[Paper]:
        """
        Search for academic papers

        Tries Semantic Scholar first, falls back to OpenAlex

        Args:
            query: Search query
            limit: Max results
            year_min: Minimum year (default 2020)

        Returns:
            List of Paper objects
        """
        query = query.strip()[:100]
        if not query:
            return []

        logger.info(f"Searching: '{query}' (limit={limit}, year>={year_min})")

        # Try Semantic Scholar first
        papers = await self._search_semantic_scholar(query, limit, year_min)

        if papers:
            logger.info(f"Semantic Scholar: found {len(papers)} papers")
            return papers

        # Fallback to OpenAlex
        logger.info("Falling back to OpenAlex...")
        papers = await self._search_openalex(query, limit, year_min)

        if papers:
            logger.info(f"OpenAlex: found {len(papers)} papers")

        return papers


# Singleton
_service: Optional[AcademicSearchService] = None


def get_academic_search_service() -> AcademicSearchService:
    global _service
    if _service is None:
        _service = AcademicSearchService()
    return _service


# Backward compatible function
async def search_papers(
    query: str,
    limit: int = 5,
    year_min: Optional[int] = 2020,
    year_max: Optional[int] = None
) -> List[Paper]:
    """Search for papers (Semantic Scholar + OpenAlex fallback)"""
    service = get_academic_search_service()
    return await service.search(query, limit=limit, year_min=year_min)
