import os
from typing import List, Dict, Any

import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from agents.fact_finder.schemas.fact_finder_schema import SourceInfo, FactFinderResult
from memory.local_store import LocalFactFinderMemory
from memory.session_store import save_fact_finder_result_session

load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"


class FirecrawlError(Exception):
    """Custom exception for Firecrawl-related errors."""


def call_firecrawl_search(statement: str, limit: int = 5) -> Dict[str, Any]:
    """
    Low-level call to Firecrawl's /v2/search endpoint for a given statement.
    """
    if not FIRECRAWL_API_KEY:
        raise FirecrawlError("FIRECRAWL_API_KEY is not set in environment")

    # CAP LIMIT AT 20
    limit = min(limit, 5)

    payload = {
        "query": statement,
        "sources": ["web", "news"],
        "limit": limit,
        "scrapeOptions": {
            "formats": [
                {
                    "type": "json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                            "description": {"type": "string"},
                            "source_name": {"type": "string"},
                            "source_type": {"type": "string"},
                            "source_class": {"type": "string"},
                            "source_country": {"type": "string"},
                            "historical_verdicts": {"type": "string"},
                            "publish_date": {"type": "string", "format": "date"},
                        },
                        "required": ["url"],
                    },
                    "prompt": (
                        "Extract the following fields for this result: "
                        "title of the article, direct URL, a brief description, "
                        "the name of the publication (source_name), the country of the publication (source_country), "
                        "historical verdicts related to the statement (historical_verdicts), "
                        "the type of publication source class (e.g. state_media/mainstream/partisan/unknown), and the publication date in dd-mm-yyyy format."
                    ),
                }
            ]
        },
    }

    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            FIRECRAWL_SEARCH_URL,
            json=payload,
            headers=headers,
            timeout=60,  # KEEP timeout at 60s as you requested
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        body = getattr(e.response, "text", None) if getattr(e, "response", None) else None
        raise FirecrawlError(f"Firecrawl API error: {e}. Body: {body}") from e


def run_fact_finder(statement: str, limit: int = 5) -> FactFinderResult:
    """
    High-level Fact-Finder logic:

    - Calls Firecrawl search.
    - Normalizes + validates results into SourceInfo objects.
    - Persists them to memory (both file-backed and session).
    - Returns a FactFinderResult instance.
    """
    api_data = call_firecrawl_search(statement=statement, limit=limit)

    all_sources: List[SourceInfo] = []
    seen_urls: set[str] = set()

    search_data = api_data.get("data", {})

    for source_type in ["news", "web"]:
        results = search_data.get(source_type, [])
        for result in results:
            structured_info = result.get("json")
            if not structured_info or not isinstance(structured_info, dict):
                continue

            url = structured_info.get("url")
            if not url or url in seen_urls:
                continue

            structured_info["source_type"] = source_type

            try:
                source = SourceInfo(**structured_info)
            except ValidationError:
                # Skip invalid entries, but continue processing others.
                continue

            all_sources.append(source)
            seen_urls.add(url)

    # Normalize statement minimally
    normalized_statement = statement.strip()

    fact_result = FactFinderResult(statement=normalized_statement, sources=all_sources)

    # Persist to file-backed local memory (so you can inspect anytime)
    file_memory = LocalFactFinderMemory()
    file_memory.save_result(fact_result)

    # Persist to in-memory session store (for this process / session)
    save_fact_finder_result_session(fact_result.model_dump())

    return fact_result