"""
TruthLens AI — Web Search Provider.

Retrieves real, verifiable search results for claim verification.
Supports:
  1. Google Custom Search (primary when credentials are provided in .env)
  2. Live Wikipedia Search API (authoritative open retrieval fallback)
Normalizes all results into standardized EvidenceItem format with source classification.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote, urlparse

import httpx

from app.core.config import settings
from app.schemas.models import EvidenceItem, EvidenceRelationship

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/api.php"


class SearchProvider:
    """Evidence retrieval provider with Google Custom Search and authoritative open fallback."""

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "TruthLensBot/1.0 (contact@truthlens.ai)"},
        )

    @property
    def is_available(self) -> bool:
        """Search is available via Google Custom Search or live open encyclopedic retrieval."""
        return True

    @property
    def has_google_cse(self) -> bool:
        """Check if Google Custom Search credentials are configured."""
        return settings.is_search_configured

    async def search(
        self,
        query: str,
        num_results: int = 5,
        date_restrict: Optional[str] = None,
    ) -> list[EvidenceItem]:
        """
        Execute an evidence search using Google CSE if configured, otherwise fallback.
        """
        if self.has_google_cse:
            try:
                results = await self._search_google(query, num_results=num_results, date_restrict=date_restrict)
                if results:
                    return results
                logger.info(f"Google CSE returned 0 results for '{query[:50]}'; attempting open retrieval fallback.")
            except Exception as e:
                logger.warning(f"Google CSE failed ({e}); switching to open retrieval fallback.")

        # Authoritative open retrieval fallback via Wikipedia API
        return await self._search_wikipedia(query, num_results=num_results)

    async def _search_google(
        self,
        query: str,
        num_results: int = 5,
        date_restrict: Optional[str] = None,
    ) -> list[EvidenceItem]:
        """Execute a Google Custom Search query."""
        params = {
            "key": settings.google_search_api_key,
            "cx": settings.google_search_engine_id,
            "q": query,
            "num": min(num_results, 10),
        }
        if date_restrict:
            params["dateRestrict"] = date_restrict

        response = await self._client.get(GOOGLE_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        evidence: list[EvidenceItem] = []

        for i, item in enumerate(items):
            try:
                url = item.get("link", "")
                parsed = urlparse(url)
                publisher = parsed.netloc.replace("www.", "") if parsed.netloc else None
                snippet = self._clean_text(item.get("snippet", ""))

                evidence.append(
                    EvidenceItem(
                        source_id=f"src_g_{i+1}",
                        title=item.get("title", "Untitled"),
                        url=url,
                        publisher=publisher,
                        published_at=self._extract_date(item),
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        snippet=snippet,
                        source_type=self._classify_source(publisher),
                        relationship=EvidenceRelationship.PARTIALLY_RELEVANT,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse Google result {i}: {e}")
                continue

        logger.info(f"Google Search for '{query[:60]}' returned {len(evidence)} results")
        return evidence

    async def _search_wikipedia(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[EvidenceItem]:
        """
        Execute an open retrieval search using the Wikipedia Query Search API.
        Provides real, traceable encyclopedia pages and excerpts.
        """
        # Clean query: strip punctuation and excessive words for keyword matching
        cleaned_query = re.sub(r'[^\w\s]', ' ', query)
        words = [w for w in cleaned_query.split() if len(w) > 2]
        search_term = " ".join(words[:12]) if words else query

        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_term,
            "format": "json",
            "srlimit": min(num_results, 8),
            "utf8": 1,
        }

        try:
            response = await self._client.get(WIKIPEDIA_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"Wikipedia search request failed: {e}")
            return []

        search_results = data.get("query", {}).get("search", [])
        evidence: list[EvidenceItem] = []

        for i, item in enumerate(search_results):
            try:
                title = item.get("title", "Untitled")
                page_url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                raw_snippet = item.get("snippet", "")
                snippet = self._clean_text(raw_snippet)

                timestamp = item.get("timestamp")
                published_at = timestamp[:10] if timestamp else None

                evidence.append(
                    EvidenceItem(
                        source_id=f"src_wiki_{i+1}",
                        title=f"{title} — Wikipedia",
                        url=page_url,
                        publisher="wikipedia.org",
                        published_at=published_at,
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        snippet=snippet,
                        source_type="encyclopedia",
                        relationship=EvidenceRelationship.PARTIALLY_RELEVANT,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse Wikipedia result {i}: {e}")
                continue

        logger.info(f"Wikipedia open search for '{search_term[:60]}' returned {len(evidence)} results")
        return evidence

    async def search_for_claim(
        self,
        claim_text: str,
        claim_type: Optional[str] = None,
    ) -> list[EvidenceItem]:
        """
        Build targeted search queries for a specific claim.
        Executes primary and contextual secondary searches, deduplicating by URL.
        """
        results: list[EvidenceItem] = []

        # 1. Primary search using the claim statement
        primary = await self.search(claim_text, num_results=5)
        results.extend(primary)

        # 2. Contextual secondary search based on category
        qualifier_map = {
            "government_scheme": "official scheme government",
            "health": "health study medical report",
            "finance": "finance regulation policy",
            "science": "scientific study evidence",
            "news": "fact check news report",
        }
        qualifier = qualifier_map.get(claim_type or "general", "fact check")
        short_claim = claim_text[:120]

        secondary = await self.search(f"{short_claim} {qualifier}", num_results=3)

        # Deduplicate results by URL
        seen_urls = {e.url for e in results}
        for item in secondary:
            if item.url not in seen_urls:
                results.append(item)
                seen_urls.add(item.url)

        # Renumber source_ids sequentially
        for idx, item in enumerate(results):
            item.source_id = f"src_{idx + 1}"

        return results

    @staticmethod
    def _clean_text(raw: str) -> str:
        """Strip HTML tags and unescape entities for clean display."""
        clean = re.sub(r"<[^<]+?>", "", raw)
        clean = html.unescape(clean)
        return re.sub(r"\s+", " ", clean).strip()

    @staticmethod
    def _extract_date(item: dict) -> Optional[str]:
        """Extract publication date from Google Custom Search metadata."""
        pagemap = item.get("pagemap", {})
        metatags = pagemap.get("metatags", [{}])
        if metatags:
            meta = metatags[0]
            for key in ("article:published_time", "datePublished", "og:article:published_time", "date"):
                if key in meta:
                    return str(meta[key])[:25]

        snippet = item.get("snippet", "")
        if snippet and len(snippet) > 10:
            parts = snippet.split(" — ", 1)
            if len(parts) == 2 and len(parts[0]) < 20:
                return parts[0]
        return None

    @staticmethod
    def _classify_source(publisher: Optional[str]) -> str:
        """Classify credibility domain type."""
        if not publisher:
            return "unknown"

        gov_indicators = [".gov", ".nic.in", ".gov.in", ".mil"]
        academic_indicators = [".edu", ".ac.", "sciencedirect.com", "nature.com"]
        news_indicators = [
            "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
            "nytimes.com", "theguardian.com", "ndtv.com", "thehindu.com",
            "hindustantimes.com", "indianexpress.com", "economictimes.indiatimes.com",
        ]
        factcheck_indicators = [
            "snopes.com", "factcheck.org", "politifact.com",
            "altnews.in", "boomlive.in", "vishvasnews.com",
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
        if "wikipedia.org" in domain_lower:
            return "encyclopedia"
        return "web"

    async def close(self):
        await self._client.aclose()


# Singleton
search_provider = SearchProvider()
