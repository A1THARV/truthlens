from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from agents.fact_finder.schemas.fact_finder_schema import FactFinderResult
from agents.pattern_analyzer.schemas.pattern_analyzer_schema import PatternAnalysisResult


@dataclass
class SessionState:
    """
    In-memory, per-process session state.

    This is intentionally NOT persistent: it lives only as long as the Python
    process is running (e.g., an ADK CLI session or a web server worker).
    """

    # Keyed by statement string (exact, stripped)
    fact_finder_results: Dict[str, FactFinderResult]
    pattern_analysis_results: Dict[str, PatternAnalysisResult]


# Global in-memory singleton for this process
_SESSION_STATE = SessionState(
    fact_finder_results={},
    pattern_analysis_results={},
)


def _normalize_statement(statement: str) -> str:
    return statement.strip()


# ---------- Fact-Finder session memory ----------

def save_fact_finder_result(result: FactFinderResult) -> None:
    """
    Save a FactFinderResult for this session, keyed by its statement.
    """
    key = _normalize_statement(result.statement)
    _SESSION_STATE.fact_finder_results[key] = result


def get_fact_finder_result(statement: str) -> Optional[FactFinderResult]:
    """
    Get FactFinderResult for this session by statement string.
    """
    key = _normalize_statement(statement)
    return _SESSION_STATE.fact_finder_results.get(key)


def get_latest_fact_finder_result() -> Optional[FactFinderResult]:
    """
    Get the most recently saved FactFinderResult, if any.
    Order is based on insertion order in the dict.
    """
    if not _SESSION_STATE.fact_finder_results:
        return None
    # Python 3.7+ dict preserves insertion order
    last_key = next(reversed(_SESSION_STATE.fact_finder_results))
    return _SESSION_STATE.fact_finder_results[last_key]


# ---------- Pattern Analyzer session memory ----------

def save_pattern_analysis_result(result: PatternAnalysisResult) -> None:
    """
    Save PatternAnalysisResult for this session, keyed by its statement.
    """
    key = _normalize_statement(result.statement)
    _SESSION_STATE.pattern_analysis_results[key] = result


def get_pattern_analysis_result(statement: str) -> Optional[PatternAnalysisResult]:
    key = _normalize_statement(statement)
    return _SESSION_STATE.pattern_analysis_results.get(key)
