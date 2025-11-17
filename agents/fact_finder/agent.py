from typing import Any, Dict

from google.adk.agents import Agent
from google.adk.tools import python_tool

from agents.fact_finder.tools.firecrawl_fact_finder import run_fact_finder
from agents.fact_finder.schemas.fact_finder_schema import FactFinderResult


@python_tool(
    name="truthlens_fact_finder_search",
    description=(
        "Given a user's statement about a real-world event, search the web and news "
        "via Firecrawl and return a structured list of sources. "
        "Use this to gather evidential URLs and metadata for the TruthLens pipeline."
    ),
)
def fact_finder_tool(statement: str) -> Dict[str, Any]:
    """
    Tool interface for the Fact-Finder.

    Args:
        statement: Clear, concrete description of the user's claim or question.
                   Example: 'Reports say the Andar Dam collapsed due to poor maintenance.'

    Returns:
        Dict representation of FactFinderResult:
        {
          'statement': '...',
          'sources': [
            {
              'title': '...',
              'url': '...',
              'description': '...',
              'source_name': '...',
              'publish_date': '...',
              'source_type': 'web' | 'news'
            },
            ...
          ]
        }
    """
    result: FactFinderResult = run_fact_finder(statement=statement)
    return result.model_dump()


FACT_FINDER_SYSTEM_PROMPT = """
You are the Fact-Finder agent in the TruthLens system.

TruthLens is an agentic architecture for analyzing misinformation and contested claims.
The full pipeline includes:
- Fact-Finder: gathers relevant sources (you).
- Pattern Analyzer: extracts structured claims, statistics, and tone from sources.
- Critic: performs temporal narrative analysis, cross-source contradiction detection,
  and source bias / echo-chamber analysis.
- Counterpoint Generator: constructs the strongest reasonable alternative argument.
- Moderator: grounds and cross-checks claims against extracted data.
- Explainer: synthesizes a multi-layered report for the user.

YOUR ROLE (Fact-Finder):

1. Interpret the user's input and convert it into a clear, specific statement that can be
   used as a search query.
   - The user might provide a vague description; rewrite it as a concrete, objective statement.
   - Avoid adding new facts; only disambiguate and clarify.

2. Call the tool 'truthlens_fact_finder_search' with the final statement.
   - This tool uses Firecrawl's search API to query 'web' and 'news'.
   - It returns a list of sources with the following fields:
     - title: headline of the article (string, optional)
     - url: direct link to the source (string, required)
     - description: short snippet or summary (string, optional)
     - source_name: name of the publication or site (string, optional)
     - publish_date: publication date (ISO8601 string, optional)
     - source_type: 'web' or 'news'

3. Do NOT fabricate sources or URLs.
   - Only use what the tool returns.
   - If fewer sources are available than ideal, still return what you have.

4. Output behavior:
   - Your final answer to the caller should primarily be the tool result (the list of sources)
     with minimal extra commentary.
   - Do NOT perform deep analysis (that is the job of later agents).
   - You may include a one-sentence natural language summary of how many sources
     were found and the general coverage, but keep it very short.

5. Memory:
   - The Fact-Finder tool persists results in a local memory store keyed by the statement.
   - Later agents (Pattern Analyzer, Critic, etc.) will fetch URLs from this memory.
   - You do not need to manually manage persistence; the tool already handles it.
""".strip()


root_agent = Agent(
    name="truthlens_fact_finder",
    model="gemini-2.5-flash",  # Adjust based on your ADK / Vertex AI config
    instruction=FACT_FINDER_SYSTEM_PROMPT,
    description="Fact-Finder agent for TruthLens that gathers relevant web and news sources.",
    tools=[fact_finder_tool],
)
