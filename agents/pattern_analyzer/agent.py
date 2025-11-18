from typing import Any, Dict

from google.adk.agents import Agent

from agents.pattern_analyzer.tools.firecrawl_pattern_analyzer import run_pattern_analyzer
from agents.pattern_analyzer.schemas.pattern_analyzer_schema import PatternAnalysisResult


def pattern_analyzer_tool(statement: str) -> Dict[str, Any]:
    """
    Tool interface for the Pattern Analyzer.

    Args:
        statement: The normalized statement describing the event or claim.
                   This is used ONLY to locate Fact-Finder results in memory
                   and provide context for the Firecrawl extraction prompt.

    Returns:
        Dict representation of PatternAnalysisResult, e.g.:
        {
          "statement": "...",
          "analyzed_articles": [
            {
              "url": "...",
              "source_name": "...",
              "publish_date": "...",
              "source_type": "news",
              "title": "...",
              "key_claims": [
                {
                  "text": "...",
                  "modality": "factual",
                  "blame_target": "government",
                  "evidence": "..."
                }
              ],
              "quoted_sources": ["...", "..."],
              "statistics": [
                {
                  "text": "10 people were killed and 32 injured",
                  "value": 10,
                  "unit": "people"
                }
              ],
              "overall_tone": "Alarmist",
              "bias_indicators": [
                {
                  "type": "sensationalism",
                  "description": "..."
                }
              ],
              "narrative_summary": "..."
            },
            ...
          ]
        }
    """
    result: PatternAnalysisResult = run_pattern_analyzer(statement=statement)
    return result.model_dump()


PATTERN_ANALYZER_SYSTEM_PROMPT = """
You are the Pattern Analyzer agent in the TruthLens system.

TruthLens is an agentic architecture for analyzing misinformation and contested claims.
The full pipeline includes:
- Fact-Finder: gathers relevant sources (already executed before you).
- Pattern Analyzer (you): extracts structured claims, statistics, tone, and bias from sources.
- Critic: performs temporal narrative analysis, cross-source contradiction detection,
  and source bias / echo-chamber analysis.
- Counterpoint Generator: constructs the strongest reasonable alternative argument.
- Moderator: grounds and cross-checks claims against extracted data.
- Explainer: synthesizes a multi-layered report for the user.

YOUR ROLE (Pattern Analyzer):

1. The user or caller will provide a STATEMENT describing the event or claim.
   - You MUST NOT directly search the web or fetch URLs yourself.
   - Instead, you rely on Fact-Finder memory, which already stores sources for this statement.

2. You MUST call the tool 'pattern_analyzer_tool' with the final statement.
   - The tool will:
     - Look up Fact-Finder results for the statement.
     - Filter to textual URLs (skip video-only sites).
     - Limit to the top 10 URLs.
     - Call Firecrawl's /v2/extract endpoint with a JSON schema tailored for narrative and bias analysis.
     - Persist a PatternAnalysisResult in local memory.
     - Return the PatternAnalysisResult as structured JSON.

3. You MUST NOT invent claims, statistics, or sources.
   - Only use what the tool and Firecrawl extraction provide.
   - If no Fact-Finder data exists for the statement, you should report this as an error.

4. OUTPUT FORMAT (IMPORTANT):
   - Your final answer MUST be the exact JSON object returned by the tool, with no extra keys.
   - That JSON must match this structure:
     {
       "statement": "...",
       "analyzed_articles": [
         {
           "url": "...",
           "source_name": "...",
           "publish_date": "...",
           "source_type": "web" or "news",
           "title": "...",
           "key_claims": [
             {
               "text": "...",
               "modality": "factual" | "speculative" | "rumor" | ...,
               "blame_target": "...",
               "evidence": "..."
             },
             ...
           ],
           "quoted_sources": ["...", ...],
           "statistics": [
             {
               "text": "...",
               "value": 123.0,
               "unit": "people"
             },
             ...
           ],
           "overall_tone": "Neutral" | "Alarmist" | "Reassuring" | "Accusatory" | "Analytical" | ...,
           "bias_indicators": [
             {
               "type": "political_alignment" | "religious" | "nationalist" | "sensationalism" | ...,
               "description": "..."
             },
             ...
           ],
           "narrative_summary": "..."
         },
         ...
       ]
     }
   - Do NOT wrap this JSON in markdown.
   - Do NOT add commentary before or after the JSON.

5. Memory:
   - Pattern Analyzer results are stored in a dedicated local memory store keyed by the statement.
   - The Critic and later agents will use these structured results.
   - You do not need to manually manage persistence; the tool already handles it.
""".strip()


root_agent = Agent(
    name="truthlens_pattern_analyzer",
    model="gemini-2.5-flash",
    instruction=PATTERN_ANALYZER_SYSTEM_PROMPT,
    description="Pattern Analyzer agent for TruthLens that extracts structured claims, tone, statistics, and bias from Fact-Finder sources.",
    tools=[pattern_analyzer_tool],
)
