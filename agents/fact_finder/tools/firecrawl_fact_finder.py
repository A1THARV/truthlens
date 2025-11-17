"""Firecrawl fact finder tool for web scraping and fact finding."""

import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class FirecrawlFactFinder:
    """Tool for finding facts using Firecrawl API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Firecrawl fact finder.
        
        Args:
            api_key: Firecrawl API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("Firecrawl API key not provided and not found in environment")
        
        self.base_url = "https://api.firecrawl.dev/v0"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for information related to a query.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with URL, title, and content
        """
        # Note: This is a placeholder implementation
        # Actual Firecrawl API integration would depend on their specific endpoints
        results = []
        
        try:
            # Example: Using a search endpoint (adjust based on actual API)
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json={
                    "query": query,
                    "limit": max_results
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
            else:
                print(f"Search failed with status code: {response.status_code}")
                
        except Exception as e:
            print(f"Error during search: {str(e)}")
        
        return results
    
    def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape content from a URL.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dictionary with scraped content
        """
        try:
            response = requests.post(
                f"{self.base_url}/scrape",
                headers=self.headers,
                json={"url": url},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Scraping failed with status code: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return {}
