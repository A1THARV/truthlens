"""Main entry point for TruthLens application."""

import os
from dotenv import load_dotenv

from agents.fact_finder.agent import FactFinderAgent
from memory.local_store import LocalStore

# Load environment variables
load_dotenv()


def main():
    """Main function to run the TruthLens application."""
    print("=" * 60)
    print("TruthLens - Fact Finder Agent")
    print("=" * 60)
    
    # Initialize memory store
    memory = LocalStore(storage_dir="data")
    print("\n✓ Memory store initialized")
    
    # Check if API key is available
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("\n⚠ Warning: FIRECRAWL_API_KEY not found in environment")
        print("Please set FIRECRAWL_API_KEY in your .env file")
        print("\nExample .env file:")
        print("FIRECRAWL_API_KEY=your_api_key_here")
        return
    
    # Initialize the agent
    try:
        agent = FactFinderAgent(api_key=api_key)
        print("✓ Fact Finder Agent initialized")
    except Exception as e:
        print(f"\n✗ Error initializing agent: {str(e)}")
        return
    
    # Example usage
    print("\n" + "=" * 60)
    print("Example Query")
    print("=" * 60)
    
    query = "What is the latest information about climate change?"
    print(f"\nQuery: {query}")
    
    try:
        result = agent.run(query=query, max_results=5)
        
        print(f"\nSummary: {result.summary}")
        print(f"\nFound {len(result.sources)} sources:")
        
        for i, source in enumerate(result.sources, 1):
            print(f"\n{i}. {source.title or 'Untitled'}")
            print(f"   URL: {source.url}")
            if source.relevance_score:
                print(f"   Relevance: {source.relevance_score:.2f}")
            print(f"   Content: {source.content[:200]}...")
        
        # Save results to memory
        memory.save(f"query_{hash(query)}", result.dict())
        print("\n✓ Results saved to memory")
        
    except Exception as e:
        print(f"\n✗ Error running query: {str(e)}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
