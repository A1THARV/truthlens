import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from hashlib import sha256

from dotenv import load_dotenv

from agents.fact_finder.schemas.fact_finder_schema import FactFinderResult

load_dotenv()

_DEFAULT_MEMORY_PATH = os.getenv("TRUTHLENS_MEMORY_PATH", "./memory/fact_finder_store.json")


class LocalFactFinderMemory:
    """
    Simple JSON-file-based memory for Fact-Finder results.

    This is a temporary solution for local development. In production, this can be
    replaced with a managed store (e.g., Firestore, Vertex AI Matching Engine).
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or _DEFAULT_MEMORY_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_store({})

    def _read_store(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def _write_store(self, data: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _key_for_statement(statement: str) -> str:
        """Create a stable key for a given statement."""
        return sha256(statement.strip().encode("utf-8")).hexdigest()

    def save_result(self, result: FactFinderResult) -> str:
        """Save a FactFinderResult, return the generated key."""
        store = self._read_store()
        key = self._key_for_statement(result.statement)
        store[key] = result.model_dump()
        self._write_store(store)
        return key

    def get_result_by_statement(self, statement: str) -> Optional[FactFinderResult]:
        """Retrieve a stored result by exact statement (hash-based lookup)."""
        store = self._read_store()
        key = self._key_for_statement(statement)
        data = store.get(key)
        if not data:
            return None
        return FactFinderResult(**data)
