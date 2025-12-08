# TruthLens – Multi-Agent Misinformation Analysis 

TruthLens is a multi-agent system that analyzes contested or complex claims by:

- Collecting and clustering **evidence from the web**.
- Extracting **structured claims, narratives, and statistics**.
- Building **implication chains** and assessing evidential support.
- Surfacing **counterpoints and alternative perspectives**.
- Exposing a **clean HTTP API** (FastAPI) suitable for web frontends.
- Running in the **cloud (Google Cloud Run)** for scalable inference.

> This project was built for practical exploration of agentic architectures for misinformation analysis.

---

## High-Level Architecture

TruthLens is organized as a set of cooperating agents:

1. **Fact-Finder**  
   - Input: `statement` (user claim).
   - Output: `FactFinderResult` — curated list of `SourceInfo` objects:
     - URLs, titles, dates, outlets, country, source type/class, short descriptions.
   - Role: Find and normalize *all potentially relevant evidence*.

2. **Pattern Analyzer**  
   - Input: latest `FactFinderResult` from local memory.
   - Output: `PatternAnalysisResult` — per-article analyses with:
     - `key_claims` (text + modality + blame_target + evidence),
     - `narrative_summary`,
     - `statistics`, `stance`, `bias_indicators`.
   - Role: Turn raw articles into structured, comparable claims and narratives.

3. **Critic (USP 1: Chain-of-Implications)**  
   - Input: latest `PatternAnalysisResult` from local memory.
   - Output: `CriticResult` with:
     - `implication_chains`: multi-step implications (A → B → C) and:
       - per-step `supporting_sources`, `refuting_sources`, `assessment`,
       - chain-level `overall_assessment` like:
         - `consistent`, `partially_supported`,
         - `contested_by_subject`, `contradicted_by_evidence`,
         - `speculative`.
     - `high_level_summary`.
     - (Future) `claim_consensus`, `narrative_phases`, `gaps_and_caveats`.
   - Role: Make the *logical structure* of the narrative explicit and evaluate support/refutation.

4. **Counterpoint**  
   - Input: latest `CriticResult` + `PatternAnalysisResult` from local memory.
   - Output: `CounterpointResult` — list of `Counterpoint` objects:
     - Attached to specific `implication_chains` and steps,
     - Typed as:
       - `subject_denial`, `alternative_explanation`,
       - `scope_limitation`, `methodological_caveat`,
       - `value_judgment`.
     - Labeled with:
       - `based_on_sources` (allowed URLs only),
       - `uses_general_knowledge` (boolean),
       - `strength` (`minor` / `moderate` / `strong`).
   - Role: Surface **good-faith counter-arguments** and **alternative lenses** on the same evidence.

5. **(Planned) Moderator & Explainer**  
   - Moderator: cross-checks agent outputs, resolves inconsistencies, arbitrates final factual view.
   - Explainer: creates a human-facing narrative report that integrates all agents.

Each agent runs as a **Google ADK agent** for CLI experimentation and is also exposed via a **FastAPI service** for frontend consumption.

---

## Core Data Flow

Given a user statement (e.g., *“Major fire breakouts in buildings in China claiming hundreds of lives”*):

1. **Fact-Finder**  
   - Crawls & queries news / web (e.g. via Firecrawl + Gemini).
   - Produces a `FactFinderResult` JSON and saves it to `memory/fact_finder_store.json`.

2. **Pattern Analyzer**  
   - Loads latest `FactFinderResult` from memory.
   - Analyzes each article into an `ArticleAnalysis`:
     - Extracts `key_claims`, `narrative_summary`, `statistics`, etc.
   - Saves `PatternAnalysisResult` into `memory/pattern_analysis_store.json`.

3. **Critic** (`agents/critic/tools/critic_tool.py`)  
   - Loads latest `PatternAnalysisResult`.
   - `implication_chains.py`:
     - Uses Gemini 2.5 Flash to propose candidate implications from article summaries.
     - Verifies each candidate against `key_claims` using fuzzy matching and modality classification.
     - For each step A → B:
       - Votes on premise/consequence as `affirmation` / `denial` / `speculation`.
       - Builds `supporting_sources` and `refuting_sources` based on how each article talks about A and B.
       - Distinguishes:
         - **Subject denial** (e.g., foreign ministry explicitly denies),
         - **Third-party refutation** (independent disproof),
       - Assigns nuanced verdicts:
         - `consistent`, `partially_supported`,
         - `contested_by_subject`,
         - `contradicted_by_evidence`,
         - `speculative`.
     - Merges similar 1-step chains (same normalized premise) into multi-step chains.
   - `critic_tool.py`:
     - Assembles `CriticResult`,
     - Derives basic gaps and caveats (e.g., single-source implications),
     - Saves to `memory/critic_store.json`.

4. **Counterpoint** (`agents/counterpoint/tools/counterpoint_tool.py`)  
   - Loads latest `CriticResult` + `PatternAnalysisResult`.
   - Builds `allowed_urls` from all analyzed articles.
   - Calls Gemini 2.5 Flash with a strict JSON-only prompt to propose counterpoints:
     - LLM *must* use only `allowed_urls` and must mark when it uses **general knowledge** beyond the sources.
   - Post-processes to:
     - Validate chain/step indices,
     - Filter `based_on_sources` to only allowed URLs,
     - Normalize types and strengths.
   - Saves `CounterpointResult` to `memory/counterpoint_store.json`.

---

## Repository Layout (Key Files)

**Agents & Tools**

- `agents/fact_finder/…`
  - Fact-Finder agent and tools.
  - `schemas/fact_finder_schema.py`: defines `FactFinderResult`, `SourceInfo`, etc.

- `agents/pattern_analyzer/…`
  - Pattern Analyzer agent and tools.
  - `schemas/pattern_analyzer_schema.py`: `PatternAnalysisResult`, `ArticleAnalysis`, `Claim`.

- `agents/critic/tools/implication_chains.py`
  - Generates and verifies implication chains from `PatternAnalysisResult`.

- `agents/critic/tools/critic_tool.py`
  - Builds `CriticResult` using implication chains and derived gaps.
  - Saves `CriticResult` via `CriticMemory`.

- `agents/critic/schemas/critic_schema.py`
  - Defines `CriticResult`, `ImplicationChain`, `ImplicationStep`, `Gap`.

- `agents/counterpoint/tools/counterpoint_tool.py`
  - Loads Critic + Pattern analyses, calls Gemini to generate counterpoints.
  - Saves `CounterpointResult` via `CounterpointMemory`.

- `agents/counterpoint/schemas/counterpoint_schema.py`
  - Defines:
    - `Counterpoint` (id, target_chain_index, target_step_index, type, text, evidence),
    - `CounterpointResult` (statement, high_level_summary, counterpoints).

- `agents/counterpoint/agent.py` (or `counterpoint_generator.py` depending on your naming)
  - ADK `Agent` that exposes `counterpoint_tool()` as a callable tool.

**Memory Layer**

- `memory/local_fact_finder_memory.py`
  - JSON-backed store for latest `FactFinderResult`.

- `memory/pattern_analysis_memory2.py`
  - JSON-backed store for latest `PatternAnalysisResult`.

- `memory/critic_memory_store.py`
  - JSON-backed store for `CriticResult` (keys by statement; typically only latest is used).

- `memory/counterpoint_memory.py`
  - JSON-backed store for latest `CounterpointResult`.

**Service & API**

- `service.py`
  - FastAPI app exposing a `/analyze` endpoint that runs:
    - Fact-Finder → Pattern Analyzer → Critic → Counterpoint,
    - Returns a combined JSON bundle.

**Infra**

- `Dockerfile`
  - Containerizes the app for Google Cloud Run.
- `requirements.txt`
  - Python dependencies (FastAPI, Uvicorn, google-generativeai, google-adk, pydantic, etc.).

---

## Running Locally

### 1. Setup

```bash
git clone <your-repo-url> truthlens
cd truthlens

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Environment variables (e.g. in `.env`):

```env
GOOGLE_API_KEY=your_gemini_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
TRUTHLENS_MEMORY_PATH=./memory/fact_finder_store.json  # optional override
TRUTHLENS_CRITIC_MEMORY_PATH=./memory/critic_store.json  # optional override
TRUTHLENS_COUNTERPOINT_MEMORY_PATH=./memory/counterpoint_store.json  # optional override
```

### 2. Running via FastAPI (end-to-end API)

Start the service:

```bash
uvicorn service:app --reload --port 8000
```

- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Example request:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"statement": "Major fire breakouts in buildings in China claiming hundreds of lives"}'
```

Response shape (simplified):

```json
{
  "statement": "...",
  "fact_finder": { ... FactFinderResult ... },
  "pattern_analysis": { ... PatternAnalysisResult ... },
  "critic": { ... CriticResult ... },
  "counterpoint": { ... CounterpointResult ... }
}
```

### 3. Running agents via ADK (CLI)

You can also run each agent interactively using **Google ADK**:

```bash
# Fact-Finder agent
adk run agents/fact_finder/truthlens

# Pattern Analyzer agent
adk run agents/pattern_analyzer/truthlens

# Critic agent
adk run agents/critic/truthlens

# Counterpoint agent
adk run agents/counterpoint/truthlens
```

Recommended order per statement:

1. Fact-Finder
2. Pattern Analyzer
3. Critic
4. Counterpoint

Each agent writes its result into the corresponding `memory/*.json` file.

---

## Deployment (Google Cloud Run)

### 1. Dockerfile

The project includes a `Dockerfile` similar to:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 2. Build and Deploy

From project root:

```bash
gcloud config set project YOUR_PROJECT_ID

gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/truthlens-api

gcloud run deploy truthlens-api \
  --image gcr.io/YOUR_PROJECT_ID/truthlens-api \
  --platform managed \
  --region YOUR_REGION \
  --allow-unauthenticated
```

Configure environment variables in the Cloud Run console:

- `GOOGLE_API_KEY`
- `FIRECRAWL_API_KEY`
- (Optional) `TRUTHLENS_*` memory paths (or use defaults).

Cloud Run will give you a URL like:

```text
https://truthlens-api-xyz-uc.a.run.app
```

Your endpoint becomes:

- `POST https://truthlens-api-xyz-uc.a.run.app/analyze`

---

## Frontend Integration (Conceptual)

A simple frontend can:

1. Let the user input a `statement`.
2. POST to `/analyze` with `{ "statement": "..." }`.
3. Render the JSON result as three main sections:

### 1. Evidence & Sources (Fact-Finder)

- List of sources:
  - Headline, outlet, country, date.
  - Tag chips like `[News] [Mainstream] [Hong Kong]`.
- Filters:
  - By country, outlet, date, source type.

### 2. Patterns & Implication Chains (Pattern Analyzer + Critic)

- Key claims:
  - “Substandard materials used during renovation” (3 sources).
  - “Fire alarms failed to activate” (1 source).
- Implication chains:
  - Cards showing:
    - Premise → Conclusion.
    - Supporting and refuting sources.
    - `overall_assessment` badge (`consistent`, `contested_by_subject`, etc.).
  - Clicking on sources reveals excerpts.

### 3. Counterpoints & Caveats (Counterpoint + Gaps)

- For each implication chain:
  - Counterpoints:
    - `[Grounded] [subject_denial]` “Chinese ministry denies the campaign, calling it ‘false and biased’.” (Source: Reuters)
    - `[Speculative] [alternative_explanation]` “Other factors such as aging infrastructure and wind conditions commonly influence fire spread.”
  - Clearly indicate:
    - `based_on_sources` (with URL links),
    - `uses_general_knowledge` (badge).
- Gaps & caveats:
  - “Single-source implication — no independent corroboration.”
  - “Contradiction comes mainly from subject denial, not independent evidence.”

This design allows users to see:

- What the **sources** say.
- How they **connect** logically.
- Where the **counterpoints** and **uncertainties** are.

---

## Technical Design Details & Trade-offs

### Agents & LLM Calls

- **Gemini 2.5 Flash** is used for:
  - Generating implication candidates from narrative summaries.
  - Generating counterpoint candidates given Critic + PatternAnalysis.
- All calls are **wrapped** with strict JSON-only prompts and then parsed in Python.
- Python post-processing:
  - Normalizes fields,
  - Deduplicates URLs,
  - Enforces schema constraints,
  - Ensures only allowed URLs are used in evidence lists.

### Memory Model

- Local JSON stores:
  - `fact_finder_store.json`
  - `pattern_analysis_store.json`
  - `critic_store.json`
  - `counterpoint_store.json`
- These are **temporary & local**, optimized for:
  - Simplicity,
  - Debuggability,
  - Small-scale demos.
- In production, they can be replaced by:
  - Cloud databases (Firestore, Postgres),
  - Object storage (GCS),
  - Or more advanced vector/graph stores.

### Performance & Latency

- Currently, `/analyze` runs the entire chain in a **single request**:
  - Fact-Finder (can be slow due to crawling / search),
  - Pattern Analyzer (moderate),
  - Critic + Counterpoint (LLM-heavy but cheaper).
- For production:
  - Split into multiple Cloud Run services:
    - `/fact-finder`, `/pattern`, `/critic`, `/counterpoint`.
  - Use the frontend to:
    - Show **incremental progress**,
    - Stream partial results (e.g., sources first, chains later).
  - Add caching per statement to avoid recomputing for repeated queries.

---

## Practical Implications & Use Cases

### 1. Journalist / Researcher Tool

- Input: “China ran an AI-powered disinformation campaign against Rafale jets.”
- Output:
  - Sources across countries,
  - Explicit chain: “US commission alleges campaign → China denies → articles report possible impact on Indonesia’s purchase.”
  - Counterpoints:
    - Subject denials,
    - Lack of Indonesian primary-source confirmation,
    - “Single-commission” evidence caveats.

This makes it easier to **write balanced pieces** and **inspect evidence structure**.

### 2. Policy & Risk Analysis

- For infrastructure tragedies (fires, collapses, accidents):
  - Identify **dominant narrative** (“substandard materials + negligence”),
  - See **alternative explanations** (e.g., weather, system design, policy failures),
  - Understand what is **firmly established** vs **politically contested**.

### 3. Media Literacy / Education

- As a classroom tool:
  - Show how the same event is covered by different outlets.
  - Visualize causal claims (A → B) and highlight:
    - Where the evidence is strong,
    - Where the story is speculative,
    - How counterpoints arise.

---

## Limitations & Future Work

- **Reliance on LLMs**  
  - While post-processing reduces hallucinations, the system still depends on:
    - LLM faithfulness to the provided JSON context,
    - Quality of Fact-Finder’s source set.

- **No full streaming yet**  
  - All stages run in one HTTP request.
  - Future: streaming responses, separate microservices, and websockets for UI updates.

- **Counterpoint depth**  
  - Current Counterpoint agent focuses on:
    - Chain-level counterpoints,
    - Basic labeling (`uses_general_knowledge`, `based_on_sources`).
  - Future: more rigorous verification, explicit logical operators, alignment with Moderator.

- **Memory**  
  - Local JSON is simple but not ideal at scale.
  - Migration path: cloud DBs with per-statement keys and versioning.

---

## Acknowledgements

This project was developed as a prototype of a multi-agent misinformation analysis system.

Technologies & Services:

- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
- [Google Gemini](https://ai.google.dev/)
- [Google Agentic Development Kit (ADK)](https://github.com/google-gemini/agentic-development-kit)
- [Google Cloud Run](https://cloud.google.com/run)

---

## Getting Involved / Extending

Ideas for future contributions:

- Implement **USP 2/3**:
  - Claim consensus across sources.
  - Temporal narrative phases.
- Add Moderator & Explainer agents:
  - Moderator: adjudicates final factual status per key claim.
  - Explainer: writes user-friendly narrative summaries with visualizations.
- Richer frontend:
  - Timeline views, interactive chain graphs, source comparison widgets.
- Pluggable search providers:
  - Additional news APIs, more granular region/language filters.

PRs and issues are welcome (especially around robustness, evaluation, and new use cases rooted in real-world misinformation patterns).
