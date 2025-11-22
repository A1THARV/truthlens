from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SessionState:
    """
    In-memory, per-process session state.

    Not persisted to disk. Cleared when the Python process ends.
    We intentionally avoid importing Pydantic models here to prevent circular imports.
    We just store plain dicts keyed by normalized statement; callers are responsible
    for converting to/from concrete models.
    """
    # Keyed by normalized statement string
    fact_finder_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pattern_analysis_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# Global singleton for this process
_SESSION_STATE = SessionState()


def _normalize_statement(statement: str) -> str:
    return statement.strip()


# ---------- Fact-Finder session memory ----------

def save_fact_finder_result_session(result_dict: Dict[str, Any]) -> None:
    """
    Save a FactFinderResult as a dict in session memory keyed by its normalized statement.
    Expected shape of result_dict:
      {
        "statement": "...",
        "sources": [...],
        ...
      }
    """
    statement = result_dict.get("statement", "")
    key = _normalize_statement(statement)
    _SESSION_STATE.fact_finder_results[key] = result_dict


def get_fact_finder_result_session(statement: str) -> Optional[Dict[str, Any]]:
    """
    Get a FactFinderResult dict from session memory by statement string.
    """
    key = _normalize_statement(statement)
    return _SESSION_STATE.fact_finder_results.get(key)


def get_latest_fact_finder_result_session() -> Optional[Dict[str, Any]]:
    """
    Get the most recently saved FactFinderResult dict, if any.
    """
    if not _SESSION_STATE.fact_finder_results:
        return None
    last_key = next(reversed(_SESSION_STATE.fact_finder_results))
    return _SESSION_STATE.fact_finder_results[last_key]


# ---------- Pattern Analyzer session memory ----------

def save_pattern_analysis_result_session(result_dict: Dict[str, Any]) -> None:
    """
    Save a PatternAnalysisResult as a dict in session memory keyed by its normalized statement.
    Expected shape:
      {
        "statement": "...",
        "analyzed_articles": [...],
        ...
      }
    """
    statement = result_dict.get("statement", "")
    key = _normalize_statement(statement)
    _SESSION_STATE.pattern_analysis_results[key] = result_dict


def get_pattern_analysis_result_session(statement: str) -> Optional[Dict[str, Any]]:
    key = _normalize_statement(statement)
    return _SESSION_STATE.pattern_analysis_results.get(key)