from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai

from agents.critic.schemas.critic_schema import (
    ImplicationChain,
    ImplicationStep,
)
from agents.pattern_analyzer.schemas.pattern_analyzer_schema import (
    ArticleAnalysis,
    Claim,
    PatternAnalysisResult,
)
from memory.pattern_analysis_store import PatternAnalysisMemory


# --- Helpers to load Pattern Analysis ----------------------------------------


def _load_latest_pattern_analysis() -> PatternAnalysisResult:
    """
    Load the latest PatternAnalysisResult from local PatternAnalysisMemory.
    """
    memory = PatternAnalysisMemory()
    store = memory._read_store()  # type: ignore[attr-defined]

    if not store:
        raise ValueError(
            "No Pattern Analysis data found in local memory. "
            "Run the Pattern Analyzer agent first."
        )

    last_key = next(reversed(store))
    data = store[last_key]
    return PatternAnalysisResult(**data)


# --- LLM candidate generation (Gemini 2.5 Flash) -----------------------------


def _generate_implication_candidates(pa: PatternAnalysisResult) -> List[Dict[str, str]]:
    """
    Use Gemini 2.5 Flash to propose candidate implication pairs (premise, consequence)
    based on article narrative summaries.

    Returns a list of dicts with keys: "premise", "consequence", "reasoning".
    """
    summaries = [
        art.narrative_summary
        for art in pa.analyzed_articles
        if art.narrative_summary
    ]
    if not summaries:
        return []

    summaries_text = "\n".join(f"- {s}" for s in summaries)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[ImplicationChains] WARNING: GOOGLE_API_KEY not set. Returning no candidates.")
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are helping to analyze logical implications in news coverage about this statement:

"{pa.statement}"

You will receive several narrative summaries of articles. From these, identify
logical implication relationships of the form:

  - premise: one event, situation, or claim (A)
  - consequence: another event, situation, or claim (B) that is presented as
                 caused by, resulting from, or logically implied by A
  - reasoning: short explanation of why the articles suggest this implication

Return ONLY a JSON array of objects with keys:
  - "premise": string
  - "consequence": string
  - "reasoning": string

Do NOT wrap the JSON in markdown fences, and do NOT add explanations.

Summaries:
{summaries_text}
""".strip()

    try:
        response = model.generate_content(prompt)
        text = (response.text or "").strip()

        # Try to clean common markdown fences if the model adds them
        if text.startswith("```"):
            # strip first and last fence
            text = text.strip("`")
            # crude but helps in many cases
        candidates = json.loads(text)
        if not isinstance(candidates, list):
            print("[ImplicationChains] LLM returned non-list JSON; ignoring.")
            return []
        # Keep only objects with required keys
        clean: List[Dict[str, str]] = []
        for c in candidates:
            if not isinstance(c, dict):
                continue
            prem = str(c.get("premise", "")).strip()
            cons = str(c.get("consequence", "")).strip()
            reas = str(c.get("reasoning", "")).strip()
            if prem and cons:
                clean.append(
                    {"premise": prem, "consequence": cons, "reasoning": reas}
                )
        return clean
    except Exception as e:
        print(f"[ImplicationChains] Error generating candidates: {e}")
        return []


# --- Verification over key_claims -------------------------------------------


def _normalize_text(t: str) -> List[str]:
    return [w for w in t.lower().replace(",", " ").replace(".", " ").split() if w]


def _jaccard_similarity(a_words: List[str], b_words: List[str]) -> float:
    if not a_words or not b_words:
        return 0.0
    sa, sb = set(a_words), set(b_words)
    inter = len(sa & sb)
    if inter == 0:
        return 0.0
    return inter / float(len(sa))


def _classify_modality(modality: Optional[str]) -> Optional[str]:
    """
    Map free-text modality into one of: 'affirmation', 'denial', 'speculation'.
    Very crude first version; refine as needed.
    """
    if not modality:
        return None

    m = modality.lower()
    if any(k in m for k in ["denies", "denied", "refutes", "refuted", "false"]):
        return "denial"
    if any(k in m for k in ["reports", "reported", "claims", "claimed", "alleges", "stated"]):
        return "affirmation"
    if any(k in m for k in ["alleged", "allegedly", "suggests", "may", "might", "possibly"]):
        return "speculation"
    # Default: treat unknown as speculation rather than hard affirmation/denial
    return "speculation"


def _check_claim_support(
    key_claims: List[Claim],
    target_text: str,
    similarity_threshold: float = 0.3,
) -> Optional[str]:
    """
    Fuzzy match target_text against a list of key claims.
    Returns classified modality ('affirmation', 'denial', 'speculation') or None.
    """
    target_words = _normalize_text(target_text)
    if not target_words:
        return None

    best_sim = 0.0
    best_modality: Optional[str] = None

    for claim in key_claims:
        claim_words = _normalize_text(claim.text)
        sim = _jaccard_similarity(target_words, claim_words)
        if sim >= similarity_threshold and sim > best_sim:
            classified = _classify_modality(claim.modality)
            if classified:
                best_sim = sim
                best_modality = classified

    return best_modality


# --- Public tool: build implication chains ----------------------------------


def build_implication_chains_tool() -> Dict[str, Any]:
    """
    Tool entrypoint for USP 1: Chain-of-Implications Verification.

    PHASE 1: Use Gemini 2.5 Flash to propose candidate implication pairs from
             article narrative summaries.
    PHASE 2: Verify each candidate against key_claims across all articles to
             determine how strongly the implication A -> B is supported or
             contradicted.

    Returns:
      {
        "statement": "...",
        "implication_chains": [ ImplicationChain-as-dict, ... ]
      }
    """
    pa: PatternAnalysisResult = _load_latest_pattern_analysis()
    articles: List[ArticleAnalysis] = pa.analyzed_articles

    # Phase 1: LLM candidate generation
    candidates = _generate_implication_candidates(pa)
    if not candidates:
        print("[ImplicationChains] No candidates generated by LLM.")
        return {"statement": pa.statement, "implication_chains": []}

    implication_chains: List[ImplicationChain] = []

    for idx, cand in enumerate(candidates, start=1):
        premise_text = cand["premise"]
        conseq_text = cand["consequence"]
        reasoning = cand.get("reasoning", "")

        premise_votes = {"affirmation": 0, "denial": 0, "speculation": 0}
        conseq_votes = {"affirmation": 0, "denial": 0, "speculation": 0}

        supporting_sources: List[str] = []
        refuting_sources: List[str] = []

        # Phase 2: Loop through articles to check support/refutation
        for art in articles:
            p_mod = _check_claim_support(art.key_claims, premise_text)
            c_mod = _check_claim_support(art.key_claims, conseq_text)

            if p_mod:
                premise_votes[p_mod] += 1
            if c_mod:
                conseq_votes[c_mod] += 1

            # Use URL as canonical source id (or fallback to source_name)
            src_label = art.url or (art.source_name or "unknown_source")

            # supported if this article affirms A AND (affirms B or speculates on B)
            if p_mod == "affirmation" and c_mod in ("affirmation", "speculation"):
                supporting_sources.append(src_label)

            # refuted if this article affirms A but denies B
            if p_mod == "affirmation" and c_mod == "denial":
                refuting_sources.append(src_label)

        # Decide chain-level verdict for this A -> B
        if len(supporting_sources) > 1 and not refuting_sources:
            overall = "consistent"
            step_assessment = (
                "well supported by multiple sources with no clear refutations"
            )
        elif len(supporting_sources) == 1 and not refuting_sources:
            overall = "partially supported"
            step_assessment = "weakly supported (single-source implication)"
        elif refuting_sources:
            overall = "contradicted"
            step_assessment = (
                "contested: at least one source affirms the premise but denies the consequence"
            )
        else:
            # Check if the premise itself is mostly denied
            if premise_votes["denial"] > premise_votes["affirmation"]:
                overall = "contradicted"
                step_assessment = (
                    "premise itself appears more often denied than affirmed"
                )
            else:
                overall = "speculative"
                step_assessment = (
                    "inferred only by LLM, with no strong article-level corroboration"
                )

        step = ImplicationStep(
            premise=premise_text,
            conclusion=conseq_text,
            supporting_sources=supporting_sources,
            refuting_sources=refuting_sources,
            assessment=step_assessment,
        )

        chain_description = f"Implication chain {idx}: {premise_text} -> {conseq_text}"
        notes = (
            f"LLM reasoning: {reasoning}. "
            f"Premise votes: {premise_votes}. Consequence votes: {conseq_votes}."
        )

        chain = ImplicationChain(
            description=chain_description,
            steps=[step],
            overall_assessment=overall,
            notes=notes,
        )
        implication_chains.append(chain)

    return {
        "statement": pa.statement,
        "implication_chains": [c.model_dump() for c in implication_chains],
    }