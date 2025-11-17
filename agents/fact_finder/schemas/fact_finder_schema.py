"""Schema definitions for fact finder agent."""

from pydantic import BaseModel, Field
from typing import List, Optional


class FactFinderInput(BaseModel):
    """Input schema for fact finder agent."""
    
    query: str = Field(..., description="The query or claim to fact-check")
    max_results: int = Field(default=5, description="Maximum number of results to return")


class FactSource(BaseModel):
    """Schema for a fact source."""
    
    url: str = Field(..., description="URL of the source")
    title: Optional[str] = Field(None, description="Title of the source")
    content: str = Field(..., description="Relevant content from the source")
    relevance_score: Optional[float] = Field(None, description="Relevance score of the source")


class FactFinderOutput(BaseModel):
    """Output schema for fact finder agent."""
    
    query: str = Field(..., description="The original query")
    sources: List[FactSource] = Field(default_factory=list, description="List of fact sources found")
    summary: Optional[str] = Field(None, description="Summary of findings")
