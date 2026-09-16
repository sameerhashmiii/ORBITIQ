# Engineering Decisions (10)

1. **PostgreSQL (+PostGIS-ready)**: normalized tables for cells/sats/devices/telemetry/events; PostGIS justifies geo queries at scale. SQLite fallback for zero-config demo.
2. **FastAPI**: typed, OpenAPI for free, async-ready for fan-out (sat propagation × devices).
3. **React + MapLibre**: MapLibre is OSS (no Mapbox token); React Router keeps NOC views composable.
4. **RandomForest (not deep learning)**: tabular telemetry, tiny data, interpretability via importances, fast CPU inference.
5. **IsolationForest for anomalies**: unlabeled ops data; contamination prior is explicit and tunable.
6. **Transparent weighted handoff scorer**: auditability > black-box RL for a demo where every recommendation must be explained.
7. **Deterministic simulation (seed 42)**: reproducibility for recruiters/CI; EMA smoothing gives temporal continuity instead of random jumps.
8. **ML and LLM separated**: ML predicts numbers; LLM only explains precomputed results → hallucination surface minimized.
9. **Data provenance labels**: trust engineering — every pixel declares REAL/DERIVED/SIMULATED/PREDICTION.
10. **Local snapshots + graceful degradation**: REAL → CACHE → SNAPSHOT → SIM chain; missing LLM/satellite/cell sources degrade loudly, never silently.
11. **Aggregation at the backend**: grid clustering/pagination so 10k+ devices never hit the browser raw.
