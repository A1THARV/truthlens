from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel


CounterpointType = Literal[
    "subject_denial",          # direct denial by an actor (e.g., Chinese FM)
    "alternative_explanation", # another plausible cause/story
    "scope_limitation",        # overgeneralization, cherry-picking
    "methodological_caveat",   # single-source, weak evidence, etc.
    "value_judgment",          # normative framing vs. factual claim
]


class Counterpoint(BaseModel):
    id: str

    # Which Critic structure this is attached to
    target_chain_index: int      # index into CriticResult.implication_chains
    target_step_index: int       # index into chain.steps

    type: CounterpointType
    text: str

    # Evidence & grounding
    based_on_sources: List[str]  # URLs from your allowed list; can be empty
    uses_general_knowledge: bool # True if this goes beyond explicit content of the sources
    strength: Literal["minor", "moderate", "strong"] = "moderate"

    notes: Optional[str] = None


class CounterpointResult(BaseModel):
    statement: str
    high_level_summary: str
    counterpoints: List[Counterpoint]