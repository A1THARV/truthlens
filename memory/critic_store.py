import json
import os
from typing import Any, Dict

from agents.critic.schemas.critic_schema import CriticResult


class CriticMemory:
    """
    Simple JSON-backed local store for CriticResult objects.

    Stores data in TRUTHLENS_CRITIC_MEMORY_PATH if set, otherwise
    defaults to ./memory/critic_store.json.

    Current strategy: keep only the latest result, keyed by its statement.
    That mirrors how you're using PatternAnalysisMemory for "latest run".
    """

    def __init__(self) -> None:
        default_path = "./memory/critic_store.json"
        self.path = os.environ.get("TRUTHLENS_CRITIC_MEMORY_PATH", default_path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

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

    def save_result(self, result: CriticResult) -> None:
        """
        Save a CriticResult, keyed by its statement.

        We clear previous entries so the store always reflects the
        latest Critic run. This keeps downstream agents simple: they
        can just load the "last" entry without worrying about history.
        """
        store = self._read_store()
        store.clear()
        store[result.statement] = result.model_dump()
        self._write_store(store)