import json
import os
from typing import Any, Dict, Optional

from agents.counterpoint.schemas.counterpoint_schema import CounterpointResult

DEFAULT_COUNTERPOINT_MEMORY_PATH = os.getenv(
    "TRUTHLENS_COUNTERPOINT_MEMORY_PATH",
    "./memory/counterpoint_store.json",
)


class CounterpointMemory:
    """
    JSON-backed local store for CounterpointResult.

    Stores ONLY the latest CounterpointResult. Each new save overwrites the previous
    result entirely.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = path or DEFAULT_COUNTERPOINT_MEMORY_PATH
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self._write_store({})

    def _read_store(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _write_store(self, store: Dict[str, Any]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)

    def save_result(self, result: CounterpointResult) -> None:
        """
        Save the latest CounterpointResult, overwriting any previous content.
        """
        self._write_store(result.model_dump())

    def get_latest_result(self) -> Optional[CounterpointResult]:
        store = self._read_store()
        if not store:
            return None
        return CounterpointResult(**store)