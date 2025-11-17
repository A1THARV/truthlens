"""Fact finder agent implementation."""

import os
from typing import Optional
from dotenv import load_dotenv

from .tools.firecrawl_fact_finder import FirecrawlFactFinder
from .schemas.fact_finder_schema import FactFinderInput, FactFinderOutput, FactSource

load_dotenv()


class FactFinderAgent:
    """Agent for finding and verifying facts."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the fact finder agent.
        
        Args:
            api_key: Firecrawl API key. If not provided, will try to get from environment.
        """
        self.fact_finder = FirecrawlFactFinder(api_key=api_key)
    
    def process(self, input_data: FactFinderInput) -> FactFinderOutput:
        """Process a fact-finding request.
        
        Args:
            input_data: Input data containing the query and parameters
            
        Returns:
            Output data with sources and summary
        """
        # Search for information
        search_results = self.fact_finder.search(
            query=input_data.query,
            max_results=input_data.max_results
        )
        
        # Convert search results to FactSource objects
        sources = []
        for result in search_results:
            source = FactSource(
                url=result.get("url", ""),
                title=result.get("title"),
                content=result.get("content", ""),
                relevance_score=result.get("score")
            )
            sources.append(source)
        
        # Generate summary (placeholder - could use LLM for better summarization)
        summary = self._generate_summary(input_data.query, sources)
        
        return FactFinderOutput(
            query=input_data.query,
            sources=sources,
            summary=summary
        )
    
    def _generate_summary(self, query: str, sources: list) -> str:
        """Generate a summary of findings.
        
        Args:
            query: The original query
            sources: List of fact sources
            
        Returns:
            Summary string
        """
        if not sources:
            return f"No sources found for query: {query}"
        
        return f"Found {len(sources)} sources related to: {query}"
    
    def run(self, query: str, max_results: int = 5) -> FactFinderOutput:
        """Convenience method to run the agent with a query string.
        
        Args:
            query: The query or claim to fact-check
            max_results: Maximum number of results to return
            
        Returns:
            Output data with sources and summary
        """
        input_data = FactFinderInput(query=query, max_results=max_results)
        return self.process(input_data)
