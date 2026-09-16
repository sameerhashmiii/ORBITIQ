# Data & Methodology — ORBITIQ

> ORBITIQ is an independent engineering research prototype inspired by the technical challenges of
> satellite-to-cellular connectivity. It uses public datasets, derived engineering features, and controlled
> simulation. It does not use proprietary SpaceX data.

## What is REAL
- **OpenCelliD cell sites** (mcc/mnc/lac/cellid/radio/lat/lon/range/samples), CC BY-SA 4.0, attributed in UI + API.
  Demo ships a 1,500-row Bay-Area snapshot (`data/sample/opencellid_sample.csv`) so it runs without an API key.
- **CelesTrak-style TLEs** propagated with SGP4 (`sgp4` lib). Demo ships 24 valid-format LEO TLEs.
- **NOAA SWPC space weather** snapshot — contextual ONLY, never claimed to predict performance.

## What is DERIVED
Elevation/azimuth/slant-range/visibility/visibility-duration from SGP4 + spherical-WGS84 ground geometry
(`backend/satellite/propagate.py`, 10° elevation mask, ±120-min scan). Km-level simplification, documented.

## What is SIMULATED
All device telemetry (RSRP/RSRQ/SINR/latency/loss/throughput/jitter/battery) from the seeded device simulator
(`SIMULATION_SEED=42`, EMA smoothing → temporal continuity, mobility profiles).

## What models PREDICT
- Anomaly score (IsolationForest, contamination 5%).
- 5-min degradation probability (RandomForest on noisy device-observable features only — load columns excluded to avoid leakage).
- Evaluated: precision **0.76**, recall **0.863**, F1 **0.808**, ROC-AUC **0.971** (`ml/evaluation/last_run.json`). No other accuracy claims are made anywhere.

## What the AI RECOMMENDS
Handoff ranking from the transparent weighted scorer (`handoff-scorer-v1`) + what-if BEFORE/AFTER from twin reruns, labeled SIMULATION RESULT.

## UI labels
Every view carries [REAL] / [DERIVED] / [SIMULATED] / [PREDICTION] / [AI RECOMMENDATION] badges. Registry: `data_sources.yaml`.
