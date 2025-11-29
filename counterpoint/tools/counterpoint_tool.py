from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import google.generativeai as genai

from agents.critic.schemas.critic_schema import CriticResult
from agents.pattern_analyzer.schemas.pattern_analyzer_schema import (
    PatternAnalysisResult,
    ArticleAnalysis,
)
from agents.counterpoint.schemas.counterpoint_schema import (
    Counterpoint,
    CounterpointResult,
)
from memory.critic_store import CriticMemory
from memory.pattern_analysis_store import PatternAnalysisMemory
from memory.local_counterpoint_store import CounterpointMemory


# --- Helpers to load upstream results ----------------------------------------


def _load_latest_critic() -> CriticResult:
    """
    Load the latest CriticResult from local CriticMemory.

    Mirrors your existing pattern: read the JSON store and take the last key.
    CriticMemory.save_result() already clears the store and keeps only one entry,
    so this effectively returns the latest Critic run.
    """
    memory = CriticMemory()
    store = memory._read_store()  # type: ignore[attr-defined]

    if not store:
        raise ValueError(
            "No CriticResult found in local memory. "
            "Run the Critic agent first."
        )

    last_key = next(reversed(store))
    data = store[last_key]
    return CriticResult(**data)


def _load_latest_pattern_analysis() -> PatternAnalysisResult:
    """
    Load the latest PatternAnalysisResult from local PatternAnalysisMemory.

    Same pattern: read underlying store and take the last key.
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


def _collect_allowed_urls(pa: PatternAnalysisResult) -> List[str]:
    urls: List[str] = []
    for art in pa.analyzed_articles:
        if art.url:
            urls.append(art.url)
    # Deduplicate while preserving order
    seen = set()
    result: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


# --- LLM call to propose counterpoints ---------------------------------------


def _generate_counterpoints_with_llm(
    statement: str,
    critic: CriticResult,
    pa: PatternAnalysisResult,
    allowed_urls: List[str],
) -> List[Dict[str, Any]]:
    """
    Use Gemini 2.5 Flash to propose counterpoints for Critic's implication chains.

    Returns a list of dicts with keys:
      - id
      - target_chain_index
      - target_step_index
      - type
      - text
      - based_on_sources (subset of allowed_urls)
      - uses_general_knowledge (bool)
      - strength
      - notes
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[Counterpoint] WARNING: GOOGLE_API_KEY not set. Returning no counterpoints.")
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    critic_json = critic.model_dump()
    pa_json = pa.model_dump()

    prompt = f"""
You are the Counterpoint agent in the TruthLens pipeline.

The upstream agents have already:
- Gathered sources about this statement.
- Extracted key claims and narrative patterns.
- Built implication chains and assessed how well each link is supported.

Your task:
- For the given CriticResult, propose thoughtful counterpoints for specific implication chains and steps.
- Counterpoints can include:
  - subject_denial: direct denials by actors in the sources.
  - alternative_explanation: plausible alternative causal stories consistent with the evidence.
  - scope_limitation: pointing out overgeneralization, cherry-picking, or missing context.
  - methodological_caveat: weaknesses in evidence (single source, unverified allegation, etc.).
  - value_judgment: highlighting where the language reflects opinions or framing rather than hard facts.

Constraints:
- You MUST base your reasoning primarily on the provided CriticResult and PatternAnalysisResult.
- You MAY use general world knowledge to suggest additional context, BUT you must label such points as uses_general_knowledge = true.
- You MUST NOT introduce any new URLs. You can only reference URLs from the allowed_urls list.
- For each counterpoint, choose zero or more URLs from allowed_urls that are most relevant.
- If you use general knowledge beyond what is clearly in the sources, set uses_general_knowledge to true.

Input:
- statement: {statement}
- critic_result (JSON): {json.dumps(critic_json, ensure_ascii=False)}
- pattern_analysis_result (JSON): {json.dumps(pa_json, ensure_ascii=False)}
- allowed_urls (JSON array): {json.dumps(allowed_urls, ensure_ascii=False)}

Output:
Return ONLY a JSON array of counterpoint objects with this exact schema:

[
  {{
    "id": "cp_1",
    "target_chain_index": 0,
    "target_step_index": 0,
    "type": "subject_denial" | "alternative_explanation" | "scope_limitation" | "methodological_caveat" | "value_judgment",
    "text": "Short but clear description of the counterpoint.",
    "based_on_sources": ["<url1>", "<url2>", ...],  // each must be in allowed_urls; can be empty
    "uses_general_knowledge": true or false,
    "strength": "minor" | "moderate" | "strong",
    "notes": "Optional additional explanation; can be empty string."
  }},
  ...
]

Do NOT wrap the JSON in markdown fences.
Do NOT add any explanation outside this JSON array.
""".strip()

    try:
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
        data = json.loads(text)
        if not isinstance(data, list):
            print("[Counterpoint] LLM returned non-list JSON; ignoring.")
            return []
        return data
    except Exception as e:
        print(f"[Counterpoint] Error generating counterpoints: {e}")
        return []


# --- Post-processing and tool interface --------------------------------------


def _clean_and_validate_counterpoints(
    raw: List[Dict[str, Any]],
    critic: CriticResult,
    allowed_urls: List[str],
) -> List[Counterpoint]:
    """
    Ensure:
      - indices are in range,
      - based_on_sources are subset of allowed_urls,
      - types/strengths are valid,
      - basic fields are non-empty.
    """
    result: List[Counterpoint] = []

    num_chains = len(critic.implication_chains)
    allowed_set = set(allowed_urls)

    for item in raw:
        try:
            cid = str(item.get("id", "")).strip()
            t_chain = int(item.get("target_chain_index", -1))
            t_step = int(item.get("target_step_index", -1))
            ctype = item.get("type", "").strip()
            text = str(item.get("text", "")).strip()

            if not cid or text == "":
                continue
            if t_chain < 0 or t_chain >= num_chains:
                continue
            if t_step < 0 or t_step >= len(critic.implication_chains[t_chain].steps):
                continue
            if ctype not in {
                "subject_denial",
                "alternative_explanation",
                "scope_limitation",
                "methodological_caveat",
                "value_judgment",
            }:
                continue

            srcs = item.get("based_on_sources", []) or []
            clean_srcs: List[str] = []
            for u in srcs:
                su = str(u).strip()
                if su in allowed_set:
                    clean_srcs.append(su)

            uses_gk = bool(item.get("uses_general_knowledge", False))
            strength = item.get("strength", "moderate")
            if strength not in {"minor", "moderate", "strong"}:
                strength = "moderate"

            notes_raw = item.get("notes", "")
            notes = str(notes_raw).strip() if notes_raw is not None else None
            if notes == "":
                notes = None

            cp = Counterpoint(
                id=cid,
                target_chain_index=t_chain,
                target_step_index=t_step,
                type=ctype,  # type: ignore[arg-type]
                text=text,
                based_on_sources=clean_srcs,
                uses_general_knowledge=uses_gk,
                strength=strength,  # type: ignore[arg-type]
                notes=notes,
            )
            result.append(cp)
        except Exception as e:
            print(f"[Counterpoint] Skipping invalid counterpoint item: {e}")
            continue

    return result


def run_counterpoint() -> CounterpointResult:
    """
    Main Counterpoint pipeline function.

    - Load latest CriticResult and PatternAnalysisResult from local memory.
    - Use Gemini 2.5 Flash to propose counterpoints for implication chains.
    - Clean and validate the counterpoints.
    - Save CounterpointResult to local CounterpointMemory.
    - Return CounterpointResult.
    """
    critic = _load_latest_critic()
    pa = _load_latest_pattern_analysis()
    allowed_urls = _collect_allowed_urls(pa)

    raw_cps = _generate_counterpoints_with_llm(
        statement=critic.statement,
        critic=critic,
        pa=pa,
        allowed_urls=allowed_urls,
    )
    counterpoints = _clean_and_validate_counterpoints(raw_cps, critic, allowed_urls)

    if counterpoints:
        high_level_summary = (
            "This analysis surfaces counterpoints and alternative perspectives on the "
            "implication chains identified by the Critic agent. It distinguishes "
            "between counterpoints grounded directly in the collected sources and "
            "those that rely on general world knowledge or broader contextual "
            "reasoning."
        )
    else:
        high_level_summary = (
            "No substantial counterpoints were identified beyond the existing "
            "implication analysis and gaps. This may indicate that the available "
            "sources present relatively aligned narratives on the core claims."
        )

    result = CounterpointResult(
        statement=critic.statement,
        high_level_summary=high_level_summary,
        counterpoints=counterpoints,
    )

    CounterpointMemory().save_result(result)
    return result


def counterpoint_tool() -> Dict[str, Any]:
    """
    Tool interface for the Counterpoint agent.

    No user arguments:
      - Uses the latest CriticResult and PatternAnalysisResult from local memory.
      - Builds a CounterpointResult via run_counterpoint().
      - Saves CounterpointResult to local CounterpointMemory.
      - Returns CounterpointResult as dict.
    """
    result = run_counterpoint()
    return result.model_dump()