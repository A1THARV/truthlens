from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Firecrawl extract schema (matches your result_schema.json)
# ---------------------------------------------------------------------------


class ExtractClaim(BaseModel):
    """
    Structured claim as returned by Firecrawl in `key_claims`.

      "key_claims": {
        "text": "string",
        "blame_target": "string",
        "modality": "string",
        "evidence": "string"
      }
    """

    text: str
    blame_target: Optional[str] = None
    modality: Optional[str] = None
    evidence: Optional[str] = None


class ExtractArticle(BaseModel):
    """
    One article as returned inside Firecrawl 'result' array.

      {
        "title": "string",
        "source_url": "string",
        "statistics": "string",
        "narrative_summary": "string",
        "key_claims": { ... ExtractClaim ... },
        "stance": "string",
        "bias_indication": "string"
      }
    """

    title: str
    source_url: str
    statistics: str
    narrative_summary: str

    key_claims: ExtractClaim

    stance: Optional[str] = None
    bias_indication: Optional[str] = None


class FirecrawlExtractResult(BaseModel):
    """
    Top-level schema for Firecrawl extract's 'data' field:

      {
        "result": [ ExtractArticle, ... ]
      }
    """

    result: List[ExtractArticle] = []


# ---------------------------------------------------------------------------
# Internal pattern analysis structures
# ---------------------------------------------------------------------------


class Claim(BaseModel):
    """
    Internal representation of a key claim in an article.
    Kept minimal on purpose: only what Firecrawl gives directly.
    """

    text: str
    modality: Optional[str] = None
    blame_target: Optional[str] = None
    evidence: Optional[str] = None


class ArticleAnalysis(BaseModel):
    url: str
    source_name: Optional[str] = None
    publish_date: Optional[str] = None       # from Fact-Finder
    source_type: Optional[str] = None
    title: Optional[str] = None

    # From Fact-Finder enrichment
    source_country: Optional[str] = None     # e.g. "India", "France"
    source_class: Optional[str] = None       # e.g. "mainstream", "state_media", "blog"

    # Claims and narrative
    key_claims: List[Claim] = []
    narrative_summary: Optional[str] = None

    # Simple textual statistics for this article (no numeric parsing)
    statistics: Optional[str] = None         # single string, as returned by Firecrawl

    # Article-level stance and bias from Firecrawl
    stance: Optional[str] = None             # string description
    bias_indicators: Optional[str] = None    # single string, not list

    # No overall_tone for now; add later when we actually fill it


class PatternAnalysisResult(BaseModel):
    statement: str
    analyzed_articles: List[ArticleAnalysis]