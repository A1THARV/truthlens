import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional

import requests
from pydantic import ValidationError

from agents.fact_finder.schemas.fact_finder_schema import FactFinderResult, SourceInfo
from agents.pattern_analyzer.schemas.pattern_analyzer_schema import (
    ArticleAnalysis,
    Claim,
    ExtractArticle,
    FirecrawlExtractResult,
    PatternAnalysisResult,
)
from memory.local_store import LocalFactFinderMemory
from memory.pattern_analysis_store import PatternAnalysisMemory
from memory.session_store import (
    get_latest_fact_finder_result_session,
    save_pattern_analysis_result_session,
)

FIRECRAWL_EXTRACT_URL = "https://api.firecrawl.dev/v2/extract"

# Hosts that are primarily video / non-text and should be skipped
NON_TEXTUAL_HOST_SUBSTRINGS = [
    "vimeo.com",
    "tiktok.com",
    "instagram.com",
]


def is_textual_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    return not any(bad in host for bad in NON_TEXTUAL_HOST_SUBSTRINGS)


def _build_extract_payload(statement: str, urls: List[str]) -> Dict[str, Any]:
    """
    Build the payload for Firecrawl /v2/extract using the result_schema.json
    you validated in the Firecrawl UI.
    """
    extract_schema = FirecrawlExtractResult.model_json_schema()

    # Short, schema-focused prompt (safe for ~500 char limit).
    prompt = (
        f'Analyze each article about: "{statement}". '
        "Return JSON with `result`: an array of objects. "
        "Each object must have: `title`, `source_url`, `statistics`, "
        "`narrative_summary`, `key_claims` (with text, blame_target, modality, evidence), "
        "`stance`, and `bias_indication`. No extra fields."
    )

    return {
        "urls": urls,
        "prompt": prompt,
        "schema": extract_schema,
        "agent": {"model": "FIRE-1"},
    }


def _start_extract_job(payload: Dict[str, Any], api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    print(f"[PatternAnalyzer] Starting Firecrawl extract job for {len(payload.get('urls', []))} URLs...")
    response = requests.post(
        FIRECRAWL_EXTRACT_URL,
        json=payload,
        headers=headers,
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    print(f"[PatternAnalyzer] Firecrawl start-job response: {repr(data)[:500]}")
    job_id = data.get("id")
    if not job_id:
        raise RuntimeError(f"Firecrawl extract response missing job id: {data}")
    return job_id


def _poll_extract_job(job_id: str, api_key: str, timeout_seconds: int = 300) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    status_url = f"{FIRECRAWL_EXTRACT_URL}/{job_id}"
    start_time = time.time()
    attempt = 0

    print(f"[PatternAnalyzer] Polling Firecrawl job {job_id} (timeout={timeout_seconds}s)...")

    while True:
        attempt += 1
        try:
            response = requests.get(status_url, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            print(f"[PatternAnalyzer] ERROR polling job {job_id} attempt {attempt}: {e}")
            if elapsed > timeout_seconds:
                raise TimeoutError(
                    f"Firecrawl extract job {job_id} polling timed out after {elapsed:.1f} seconds. "
                    f"Last error: {e}"
                ) from e
            time.sleep(5)
            continue

        status = data.get("status")
        print(f"[PatternAnalyzer] Job {job_id} attempt {attempt} status: {status!r}")

        if status == "completed":
            print(f"[PatternAnalyzer] Job {job_id} completed.")
            return data

        if status in {"failed", "error"}:
            raise RuntimeError(f"Firecrawl extract job {job_id} failed: {data}")

        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            raise TimeoutError(
                f"Firecrawl extract job {job_id} did not complete within {timeout_seconds} seconds. "
                f"Last known status: {status}"
            )

        time.sleep(5)


def run_pattern_analyzer() -> PatternAnalysisResult:
    """
    Pattern Analyzer workflow with batching and verbose debugging.
    """
    print("[PatternAnalyzer] Loading latest Fact-Finder result from session/local...")

    fact_result_dict = get_latest_fact_finder_result_session()
    fact_result: Optional[FactFinderResult] = None

    if fact_result_dict is not None:
        print("[PatternAnalyzer] Found Fact-Finder result in session.")
        fact_result = FactFinderResult(**fact_result_dict)
    else:
        print("[PatternAnalyzer] No session result; falling back to LocalFactFinderMemory.")
        fact_memory = LocalFactFinderMemory()
        store = fact_memory._read_store()  # type: ignore[attr-defined]
        if not store:
            raise ValueError(
                "No Fact-Finder data found in session or local memory. "
                "Run the Fact-Finder agent first."
            )
        last_key = next(reversed(store))
        fact_result = FactFinderResult(**store[last_key])

    if not fact_result.sources:
        raise ValueError("Fact-Finder returned no sources to analyze.")

    statement = fact_result.statement
    print(f"[PatternAnalyzer] Using statement: {statement!r}")

    textual_sources: List[SourceInfo] = [
        src for src in fact_result.sources if src.url and is_textual_url(src.url)
    ]
    print(f"[PatternAnalyzer] Total textual sources: {len(textual_sources)}")
    if not textual_sources:
        raise ValueError("No textual sources available (non-video) to analyze for this statement.")

    BATCH_SIZE = 5
    batches: List[List[SourceInfo]] = [
        textual_sources[i : i + BATCH_SIZE] for i in range(0, len(textual_sources), BATCH_SIZE)
    ]
    print(f"[PatternAnalyzer] URL batches: {len(batches)} (batch size {BATCH_SIZE})")

    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY is not set in the environment.")

    all_articles: List[ArticleAnalysis] = []

    for batch_index, batch_sources in enumerate(batches, start=1):
        urls = [src.url for src in batch_sources if src.url]
        if not urls:
            print(f"[PatternAnalyzer] Batch {batch_index} has no URLs, skipping.")
            continue

        print(
            f"[PatternAnalyzer] Starting Firecrawl job for batch {batch_index} "
            f"with {len(urls)} URLs."
        )

        payload = _build_extract_payload(statement=statement, urls=urls)

        try:
            job_id = _start_extract_job(payload=payload, api_key=api_key)
        except Exception as e:
            print(f"[PatternAnalyzer] ERROR starting extract job for batch {batch_index}: {e}")
            continue

        print(
            f"[PatternAnalyzer] Job {job_id} started for batch {batch_index}, "
            "polling for completion..."
        )

        try:
            job_result = _poll_extract_job(job_id=job_id, api_key=api_key, timeout_seconds=300)
        except TimeoutError as e:
            print(f"[PatternAnalyzer] TIMEOUT polling job {job_id} for batch {batch_index}: {e}")
            continue
        except Exception as e:
            print(f"[PatternAnalyzer] ERROR polling job {job_id} for batch {batch_index}: {e}")
            continue

        print(f"[PatternAnalyzer] Job {job_id} for batch {batch_index} completed. Processing data...")

        data_raw = job_result.get("data")
        print(
            f"[PatternAnalyzer] Raw 'data' for batch {batch_index}: "
            f"type={type(data_raw)}, repr={repr(data_raw)[:500]}"
        )

        if not isinstance(data_raw, dict):
            print(f"[PatternAnalyzer] Unexpected 'data' type for batch {batch_index}, skipping.")
            continue

        try:
            extract = FirecrawlExtractResult.model_validate(data_raw)
        except ValidationError as e:
            print(f"[PatternAnalyzer] ValidationError for batch {batch_index}: {e}")
            continue

        source_lookup_by_url: Dict[str, SourceInfo] = {
            src.url: src for src in batch_sources if src.url
        }

        batch_article_count_before = len(all_articles)

        for extracted in extract.result:
            src = source_lookup_by_url.get(extracted.source_url)

            # Build key_claims list (single structured claim from Firecrawl)
            claims: List[Claim] = []
            if extracted.key_claims and extracted.key_claims.text:
                claims.append(
                    Claim(
                        text=extracted.key_claims.text,
                        modality=extracted.key_claims.modality,
                        blame_target=extracted.key_claims.blame_target,
                        evidence=extracted.key_claims.evidence,
                    )
                )

            article = ArticleAnalysis(
                url=extracted.source_url,
                source_name=getattr(src, "source_name", None) if src else None,
                publish_date=getattr(src, "publish_date", None) if src else None,
                source_type=getattr(src, "source_type", None) if src else None,
                title=extracted.title or (getattr(src, "title", None) if src else None),
                source_country=getattr(src, "source_country", None) if src else None,
                source_class=getattr(src, "source_class", None) if src else None,
                key_claims=claims,
                narrative_summary=extracted.narrative_summary,
                statistics=extracted.statistics or None,
                stance=extracted.stance,
                bias_indicators=extracted.bias_indication or None,
            )

            all_articles.append(article)

        batch_article_count_after = len(all_articles)
        print(
            f"[PatternAnalyzer] Batch {batch_index} contributed "
            f"{batch_article_count_after - batch_article_count_before} articles. "
            f"Total so far: {batch_article_count_after}."
        )

    if not all_articles:
        raise RuntimeError(
            "Pattern Analyzer could not extract structured data from any article across all batches."
        )

    result = PatternAnalysisResult(statement=fact_result.statement, analyzed_articles=all_articles)

    print("[PatternAnalyzer] Saving PatternAnalysisResult to local and session memory.")
    pattern_memory = PatternAnalysisMemory()
    pattern_memory.save_result(result)

    save_pattern_analysis_result_session(result.model_dump())

    print("[PatternAnalyzer] Done. Returning result.")
    return result