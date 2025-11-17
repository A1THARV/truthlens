from pydantic import BaseModel
from typing import Optional, List


class SourceInfo(BaseModel):
    """
    Defines the structured data for a single source found by the Fact-Finder.
    Mirrors the Firecrawl search result fields we care about.
    """
    title: Optional[str] = None
    url: str
    description: Optional[str] = None
    source_name: Optional[str] = None
    publish_date: Optional[str] = None
    source_type: str  # 'web' or 'news'


class FactFinderResult(BaseModel):
    """
    Envelope for storing/searching results per user statement.
    """
    statement: str
    sources: List[SourceInfo]
