from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class ImplicationStep(BaseModel):
    """
    One logical edge in a reasoning chain, e.g.:
      premise: "China ran an AI disinfo campaign"
      conclusion: "Indonesia cancelled a Rafale deal"
    """

    premise: str
    conclusion: str

    # Names or URLs of sources that support the implication (premise -> conclusion)
    supporting_sources: List[str] = []

    # Names or URLs of sources that contradict either the premise or the conclusion
    refuting_sources: List[str] = []

    # Short free-text note: why this step is weak/strong/uncertain
    assessment: str


class ImplicationChain(BaseModel):
    """
    A chain of implications, e.g. A -> B -> C, with an overall verdict.
    """

    description: str  # human-friendly description of the chain
    steps: List[ImplicationStep] = []
    overall_assessment: str  # "consistent", "partially supported", "contradicted", "speculative"
    notes: Optional[str] = None


class ClaimConsensus(BaseModel):
    """
    How widely a canonical claim is supported/refuted across sources.
    """

    canonical_claim: str

    supporting_sources: List[str] = []
    refuting_sources: List[str] = []
    ignoring_sources: List[str] = []

    consensus_assessment: str  # "high consensus", "contested", "isolated"
    notes: Optional[str] = None


class NarrativePhase(BaseModel):
    """
    A phase in time, describing how coverage and reasoning change.
    """

    phase_name: str  # e.g. "early_rumor", "official_response", "meta_analysis"
    time_range: str  # free text like "2025-05-10 to 2025-05-13"
    description: str
    key_sources: List[str] = []  # names/URLs that best represent this phase


class Gap(BaseModel):
    """
    A notable missing piece of evidence, missing link in a chain, or blind spot in coverage.
    """

    description: str
    affected_chains: List[str] = []  # references ImplicationChain.description or ids
    why_it_matters: str


class CriticResult(BaseModel):
    """
    Top-level output of the Critic agent.

    This is what downstream agents (Counterpoint, Moderator, Explainer) will consume.
    """

    statement: str

    # 2–4 sentences summarizing the narrative + major findings
    high_level_summary: str

    implication_chains: List[ImplicationChain] = []
    claim_consensus: List[ClaimConsensus] = []
    narrative_phases: List[NarrativePhase] = []
    gaps_and_caveats: List[Gap] = []