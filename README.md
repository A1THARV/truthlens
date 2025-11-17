# TruthLens – Agentic Misinformation Analysis

This repository contains the initial implementation of the **TruthLens** agentic system, starting with the **Fact-Finder** agent.

## Architecture Overview

TruthLens is designed as a set of cooperating agents:

1. **Fact-Finder (Data Ingestion)**  
   - Uses Firecrawl APIs to search web + news for sources related to a user statement.  
   - Stores structured metadata in a shared memory store.

2. **Pattern Analyzer (Structured Data Extractor)**  
   - Uses Firecrawl extract APIs to turn pages into structured data (claims, statistics, tone).

3. **Critic (Analytical Core / USP)**  
   - Temporal narrative analysis, cross-source contradiction detection, and source bias / echo-chamber analysis.

4. **Counterpoint Generator**  
   - Generates the strongest reasonable counter-narrative without inventing new facts.

5. **Moderator (Grounding & Consistency)**  
   - Verifies all claims in final output are grounded in extracted data and checks logical consistency.

6. **Explainer (User-Facing Report)**  
   - Produces a multi-layered report for end users (confidence scores, key findings, narrative shift, sources, etc.).

This repository currently focuses on the **Fact-Finder** agent only.

## Directory Layout

```text
truthlens/
├── agents/
│   ├── __init__.py
│   └── fact_finder/
│       ├── __init__.py
│       ├── agent.py
│       ├── tools/
│       │   ├── __init__.py
│       │   └── firecrawl_fact_finder.py
│       └── schemas/
│           ├── __init__.py
│           └── fact_finder_schema.py
├── memory/
│   ├── __init__.py
│   └── local_store.py
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Setup

1. Create a virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file (based on `.env.example`):

```bash
cp .env.example .env
```

3. Edit `.env` and set:

```bash
FIRECRAWL_API_KEY=your_real_firecrawl_api_key
TRUTHLENS_MEMORY_PATH=./memory/fact_finder_store.json
```

## Running the Fact-Finder Agent Locally

```bash
python main.py
```

You’ll be prompted for a statement (e.g., `recent delhi bomb blast and its link with terrorism`).

The Fact-Finder agent will:

1. Interpret your input as a clear statement.
2. Call the Firecrawl-based tool to search web + news.
3. Store the resulting sources in local JSON memory.
4. Print the structured result.

## Next Steps

- Add the Pattern Analyzer agent (Firecrawl extract + ArticleAnalysis schema).
- Add Critic, Counterpoint, Moderator, Explainer agents.
- Move memory to a managed data store (e.g., Firestore / Vertex AI Matching Engine).
- Deploy agents to GCP (Vertex AI) once local iteration stabilizes.
