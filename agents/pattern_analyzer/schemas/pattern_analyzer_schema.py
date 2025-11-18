from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Claim(BaseModel):
    text: str
    modality: Optional[str] = None  # "factual", "speculative", "rumor", etc.
    blame_target: Optional[str] = None  # e.g. "government", "group", "community"
    evidence: Optional[str] = None  # text description of cited evidence, if any


class BiasIndicator(BaseModel):
    type: str  # "political_alignment", "religious", "nationalist", "sensationalism", etc.
    description: str  # explanation of why this article appears to have this bias


class Statistic(BaseModel):
    text: str  # e.g. "10 people were killed and 32 injured"
    value: Optional[float] = None  # numeric value if extractable
    unit: Optional[str] = None  # e.g. "people", "injured"


class ArticleAnalysis(BaseModel):
    url: str
    source_name: Optional[str] = None
    publish_date: Optional[str] = None
    source_type: Optional[str] = None  # 'web' or 'news'
    title: Optional[str] = None

    key_claims: List[Claim]
    quoted_sources: List[str]
    statistics: List[Statistic]
    overall_tone: str  # e.g. "Neutral", "Alarmist", "Reassuring", "Accusatory"
    bias_indicators: List[BiasIndicator]
    narrative_summary: str  # 2–4 sentence summary of how this article frames the event


class PatternAnalysisResult(BaseModel):
    statement: str
    analyzed_articles: List[ArticleAnalysis]


# Internal schema for Firecrawl extraction (JSON shape returned by extract)
class FirecrawlClaim(BaseModel):
    text: str
    modality: Optional[str] = None
    blame_target: Optional[str] = None
    evidence: Optional[str] = None


class FirecrawlStatistic(BaseModel):
    text: str
    value: Optional[float] = None
    unit: Optional[str] = None


class FirecrawlBiasIndicator(BaseModel):
    type: str
    description: str


class FirecrawlArticleExtractSchema(BaseModel):
    key_claims: List[FirecrawlClaim]
    quoted_sources: List[str]
    statistics: List[FirecrawlStatistic]
    overall_tone: str
    bias_indicators: List[FirecrawlBiasIndicator]
    narrative_summary: str
