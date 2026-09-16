# Architecture — ORBITIQ

```
REAL PUBLIC DATA
       ↓
DATA INGESTION (backend/data/ingest.py: REAL → CACHE → SNAPSHOT → SIM)
       ↓
DATA NORMALIZATION (Pydantic schemas + Postgres/PostGIS-ready models)
       ↓
DIGITAL TWIN (backend/services/digital_twin.py)
       ├───────┬─────────┐
       ↓       ↓         ↓
      ML   SIMULATION  NETWORK
 (anomaly,  (devices,  (cells,
  degrad.,   events,    sats,
  handoff)   telemetry) topology)
       └───────┴─────────┘
       ↓
OPTIMIZATION (handoff scorer + what-if)
       ↓
GENAI COPILOT (grounded: telemetry → structured ctx → LLM)
       ↓
COMMAND CENTER (React + MapLibre)
```

## Key flows
- **Telemetry path**: simulator (EMA-smoothed, seeded) → twin aggregation (grid clustering, never raw 10k to browser) → map/API.
- **ML path**: features v1 (`backend/ml/features.py`) → IsolationForest / RandomForest artifacts in `ml/models/demo/` → versioned APIs.
- **Decision path**: visibility geometry (SGP4+WGS84 approx) × ML predictions × load → weighted handoff scorer with per-factor explanation.
- **GenAI path**: user question + twin/ML/optimizer outputs → structured context → LLM explains; refuses when data missing; template fallback when no LLM key so the network functions always work.
- **Persistence path**: the in-memory twin stays authoritative for live state; decisions (recommendations, prediction samples), events, simulation runs, and reference data (cells, satellites, registry) persist to Postgres/PostGIS, with a local SQLite fallback. All writes are best-effort and never fail a request.

## Why this shape
AI is one component, not the system: physics does geometry, data engineering does ingestion, simulation does behavior, ML does prediction, optimization does ranking, GenAI does explanation. See `docs/engineering-decisions.md`.
