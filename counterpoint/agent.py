from typing import Any, Dict

from google.adk.agents import Agent

from agents.counterpoint.tools.counterpoint_tool import counterpoint_tool


def counterpoint_agent_tool() -> Dict[str, Any]:
    """
    Tool interface for the Counterpoint agent when used via ADK.

    It simply runs the local counterpoint_tool (which:
      - loads latest CriticResult + PatternAnalysisResult from memory,
      - computes CounterpointResult,
      - saves it to CounterpointMemory,
      - returns it as dict)
    and passes that JSON directly back to the caller.
    """
    return counterpoint_tool()


COUNTERPOINT_SYSTEM_PROMPT = """
You are the Counterpoint agent in the TruthLens system.

TruthLens is an agentic architecture for analyzing misinformation and contested claims:
- Fact-Finder: gathers relevant web and news sources.
- Pattern Analyzer: extracts structured claims, statistics, tone.
- Critic: performs implication-chain analysis and contradiction detection.
- Counterpoint (YOU): surfaces counter-arguments and alternative perspectives.
- Moderator: grounds claims against extracted data.
- Explainer: synthesizes a multi-layered report for users.

YOUR ROLE (Counterpoint):

- You MUST call the 'counterpoint_agent_tool' tool with NO arguments.
- That tool will return a JSON object of type CounterpointResult, which contains:
  - statement
  - high_level_summary
  - counterpoints: a list of counterpoints, each with:
      - id
      - target_chain_index
      - target_step_index
      - type
      - text
      - based_on_sources
      - uses_general_knowledge
      - strength
      - notes

- You MUST return exactly the JSON object produced by the tool.
- Do NOT modify its structure or fields.
- Do NOT add any commentary before or after the JSON.
- Do NOT invent new fields or change field names.

Your goal is simply to trigger the underlying tool and pass through its structured result.
""".strip()


root_agent = Agent(
    name="truthlens_counterpoint",
    model="gemini-2.5-flash",
    instruction=COUNTERPOINT_SYSTEM_PROMPT,
    description="Surfaces structured counterpoints for Critic implication chains.",
    tools=[counterpoint_agent_tool],
)