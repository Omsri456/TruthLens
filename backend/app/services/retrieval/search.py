"""
TruthLens AI — Web Search Provider (Google Custom Search).

Retrieves real search results for claim verification.
Normalizes results into EvidenceItem format.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.schemas.models import EvidenceItem, EvidenceRelationship

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


class SearchProvider:
    """Google Custom Search backed evidence retrieval."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)

    @property
    def is_available(self) -> bool:
        return settings.is_search_configured

    async def search(
        self,
        query: str,
        num_results: int = 5,
        date_restrict: Optional[str] = None,
    ) -> list[EvidenceItem]:
        """
        Execute a web search and return normalized evidence items.

        Args:
            query: The search query string.
            num_results: Number of results to request (max 10).
            date_restrict: Optional date restriction (e.g., "y1" for past year).
        """
        if not self.is_available:
            logger.warning("Search not configured. Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID.")
            return []

        params = {
            "key": settings.google_search_api_key,
            "cx": settings.google_search_engine_id,
            "q": query,
            "num": min(num_results, 10),
        }
        if date_restrict:
            params["dateRestrict"] = date_restrict

        try:
            response = await self._client.get(GOOGLE_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Search API HTTP error: {e.response.status_code} — {e.response.text[:300]}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Search API request error: {e}")
            return []
        except Exception as e:
            logger.error(f"Search failed unexpectedly: {e}")
            return []

        items = data.get("items", [])
        evidence = []
        for i, item in enumerate(items):
            try:
                url = item.get("link", "")
                parsed = urlparse(url)
                publisher = parsed.netloc.replace("www.", "") if parsed.netloc else None

                evidence.append(EvidenceItem(
                    source_id=f"src_{i+1}",
                    title=item.get("title", "Untitled"),
                    url=url,
                    publisher=publisher,
                    published_at=self._extract_date(item),
                    retrieved_at=datetime.utcnow().isoformat(),
                    snippet=item.get("snippet", ""),
                    source_type=self._classify_source(publisher),
                    relationship=EvidenceRelationship.PARTIALLY_RELEVANT,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse search result {i}: {e}")
                continue

        logger.info(f"Search for '{query[:60]}' returned {len(evidence)} results")
        return evidence

    async def search_for_claim(self, claim_text: str, claim_type: Optional[str] = None) -> list[EvidenceItem]:
        """
        Build targeted search queries for a specific claim.
        Runs up to 2 complementary searches for better coverage.
        """
        results: list[EvidenceItem] = []

        # Primary search: the claim text itself
        primary = await self.search(claim_text, num_results=5)
        results.extend(primary)

        # Secondary search: add context based on claim type
        if claim_type and claim_type != "general":
            qualifier_map = {
                "government_scheme": "official announcement",
                "health": "health authority statement",
                "finance": "official regulation",
                "science": "scientific research",
                "news": "news report verification",
            }
            qualifier = qualifier_map.get(claim_type, "fact check")
            # Use a shorter version of the claim for the secondary search
            short_claim = claim_text[:100] if len(claim_text) > 100 else claim_text
            secondary = await self.search(f"{short_claim} {qualifier}", num_results=3)

            # Deduplicate by URL
            seen_urls = {e.url for e in results}
            for item in secondary:
                if item.url not in seen_urls:
                    results.append(item)
                    seen_urls.add(item.url)

        return results

    @staticmethod
    def _extract_date(item: dict) -> Optional[str]:
        """Try to extract a publication date from search result metadata."""
        # Google sometimes includes metatags with dates
        pagemap = item.get("pagemap", {})
        metatags = pagemap.get("metatags", [{}])
        if metatags:
            meta = metatags[0]
            for key in ("article:published_time", "datePublished", "og:article:published_time", "date"):
                if key in meta:
                    return meta[key][:25]  # Truncate to reasonable length
        # Check snippet for date patterns (Google often prepends dates)
        snippet = item.get("snippet", "")
        if snippet and len(snippet) > 10:
            # Google format: "Jan 1, 2024 — ..."
            parts = snippet.split(" — ", 1)
            if len(parts) == 2 and len(parts[0]) < 20:
                return parts[0]
        return None

    @staticmethod
    def _classify_source(publisher: Optional[str]) -> str:
        """Basic source classification based on domain."""
        if not publisher:
            return "unknown"

        gov_indicators = [".gov", ".nic.in", ".gov.in", ".mil"]
        academic_indicators = [".edu", ".ac."]
        news_indicators = [
            "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
            "nytimes.com", "theguardian.com", "ndtv.com", "thehindu.com",
        ]
        factcheck_indicators = [
            "snopes.com", "factcheck.org", "politifact.com",
            "altnews.in", "boomlive.in",
        ]

        domain_lower = publisher.lower()
        if any(ind in domain_lower for ind in gov_indicators):
            return "government"
        if any(ind in domain_lower for ind in academic_indicators):
            return "academic"
        if any(ind in domain_lower for ind in factcheck_indicators):
            return "fact_check"
        if any(ind in domain_lower for ind in news_indicators):
            return "established_news"
        return "web"

    async def close(self):
        await self._client.aclose()


# Singleton
search_provider = SearchProvider()
