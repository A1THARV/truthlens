from __future__ import annotations

from typing import Any, Dict, List

from agents.critic.schemas.critic_schema import CriticResult, ImplicationChain
from agents.critic.tools.implication_chains import build_implication_chains_tool
from agents.pattern_analyzer.schemas.pattern_analyzer_schema import (
    ArticleAnalysis,
    PatternAnalysisResult,
)
from memory.critic_store import CriticMemory
from memory.pattern_analysis_store import PatternAnalysisMemory


def _load_latest_pattern_analysis() -> PatternAnalysisResult:
    """
    Load the latest PatternAnalysisResult from local PatternAnalysisMemory.

    Assumes Pattern Analyzer has run recently and cleared old entries.
    """
    memory = PatternAnalysisMemory()
    store = memory._read_store()  # type: ignore[attr-defined]

    if not store:
        raise ValueError(
            "No Pattern Analysis data found in local memory. "
            "Run the Pattern Analyzer agent first."
        )

    # Assuming insertion order is preserved, take the last key
    last_key = next(reversed(store))
    data = store[last_key]
    return PatternAnalysisResult(**data)


def critic_input_tool() -> Dict[str, Any]:
    """
    (Legacy) Tool interface that just exposes the raw PatternAnalysisResult +
    sorted articles, without building CriticResult.

    You can keep this for debugging or remove it once everything uses run_critic().
    """
    pa: PatternAnalysisResult = _load_latest_pattern_analysis()

    def _sort_key(a: ArticleAnalysis) -> str:
        return a.publish_date or ""

    sorted_articles: List[ArticleAnalysis] = sorted(pa.analyzed_articles, key=_sort_key)

    allowed_urls = [a.url for a in pa.analyzed_articles]

    return {
        "pattern_analysis": pa.model_dump(),
        "articles_sorted_by_date": [a.model_dump() for a in sorted_articles],
        "allowed_urls": allowed_urls,
    }


def run_critic() -> CriticResult:
    """
    Main Critic pipeline function.

    Mirrors the pattern of run_pattern_analyzer():
      - Load latest PatternAnalysisResult from local PatternAnalysisMemory.
      - Use internal tools (starting with implication_chains) to build structured
        CriticResult for USP 1.
      - Save CriticResult to local CriticMemory.
      - Return CriticResult.

    For now, this implements ONLY USP 1 (Chain-of-Implications) and leaves
    other sections empty. We'll plug in additional tools (claim consensus,
    narrative phases, gaps) here later.
    """
    # 1) Load latest PatternAnalysisResult
    pa: PatternAnalysisResult = _load_latest_pattern_analysis()

    # 2) Build implication chains using the existing tool.
    #    This returns a dict:
    #      { "statement": "...", "implication_chains": [ {...}, ... ] }
    chains_payload: Dict[str, Any] = build_implication_chains_tool()

    raw_chains = chains_payload.get("implication_chains", [])
    implication_chains: List[ImplicationChain] = [
        ImplicationChain(**c) for c in raw_chains
    ]

    # 3) Build a minimal high_level_summary.
    #    For now we keep this simple; later you can:
    #      - call a small LLM helper, or
    #      - compute a more descriptive summary from chains + pattern_analysis.
    if implication_chains:
        high_level_summary = (
            "This analysis identifies one or more chains of implications between claims "
            "found in the analyzed articles and evaluates how well each step is supported "
            "by the available sources. Other USP sections (claim consensus, temporal "
            "phases, gaps) are not yet computed in this version."
        )
    else:
        high_level_summary = (
            "No clear implication chains were detected from the narrative summaries of "
            "the analyzed articles. Other USP sections are not yet computed."
        )

    # 4) Assemble CriticResult for USP 1 only.
    result = CriticResult(
        statement=pa.statement,
        high_level_summary=high_level_summary,
        implication_chains=implication_chains,
        claim_consensus=[],
        narrative_phases=[],
        gaps_and_caveats=[],
    )

    # 5) Persist CriticResult in local CriticMemory (latest only).
    critic_memory = CriticMemory()
    critic_memory.save_result(result)

    return result


def critic_tool() -> Dict[str, Any]:
    """
    Tool interface for the Critic, analogous to pattern_analyzer_tool.

    No user arguments:
      - Uses the latest PatternAnalysisResult from local memory.
      - Builds a CriticResult (currently USP 1 only) via run_critic().
      - Saves CriticResult to local CriticMemory.
      - Returns CriticResult as dict.
    """
    result: CriticResult = run_critic()
    return result.model_dump()