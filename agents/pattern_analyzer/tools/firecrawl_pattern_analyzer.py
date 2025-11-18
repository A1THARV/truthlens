from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from agents.pattern_analyzer.schemas.pattern_analyzer_schema import PatternAnalysisResult


DEFAULT_PATTERN_ANALYSIS_MEMORY_PATH = Path("memory/pattern_analysis_store.json")


class PatternAnalysisMemory:
    """
    Simple JSON-file-backed memory for PatternAnalyzer results.

    Keyed by a hash of the statement to keep keys manageable and consistent
    across Fact-Finder and Pattern Analyzer.
    """

    def __init__(self, path: Path | str = DEFAULT_PATTERN_ANALYSIS_MEMORY_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_store({})

    def _read_store(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Corrupted file; reset
            return {}

    def _write_store(self, data: dict) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _statement_key(statement: str) -> str:
        return hashlib.sha256(statement.strip().encode("utf-8")).hexdigest()

    def save_result(self, result: PatternAnalysisResult) -> None:
        store = self._read_store()
        key = self._statement_key(result.statement)
        store[key] = result.model_dump()
        self._write_store(store)

    def get_result_by_statement(self, statement: str) -> Optional[PatternAnalysisResult]:
        store = self._read_store()
        key = self._statement_key(statement)
        data = store.get(key)
        if not data:
            return None
        try:
            return PatternAnalysisResult.model_validate(data)
        except ValidationError:
            return None
