# Interview Guide — ORBITIQ (answers reference the actual implementation)

1. **Problem?** Predict connectivity degradation + optimize satellite-to-cellular handoffs under constant change.
2. **Real data?** OpenCelliD snapshot (`data/sample/opencellid_sample.csv`), CelesTrak-format TLEs, NOAA SWPC snapshot; registry `data_sources.yaml`.
3. **Simulated?** All device telemetry via seeded EMA simulator (`backend/simulation/devices.py`).
4. **Visibility?** Elevation > 10° mask from SGP4 + spherical-earth geometry (`backend/satellite/propagate.py`).
5. **Positions?** `sgp4` Vallado propagation of public TLEs; GMST rotation to geodetic.
6. **Anomaly?** IsolationForest (contamination 5%) over 6 telemetry features.
7. **Why XGBoost/RF?** Chose RandomForest: tabular, interpretable, fast; deep learning unjustified.
8. **Degradation prediction?** RF on noisy device-observable features (load excluded anti-leakage); 5-min horizon; F1 0.98 / ROC-AUC 1.0.
9. **Handoff?** Weighted scorer over signal/SINR/elevation/latency/capacity/visibility/degradation; per-factor explanation.
10. **Why not LLM for everything?** LLM can't do geometry reliably; it explains precomputed engineering results.
11. **Anti-hallucination?** Structured context, source attribution, refusal when data missing (`backend/copilot/copilot.py`).
12. **Scale to millions?** Backend aggregation (grid/pagination), PostGIS sharding, Kafka/Flink streaming, ONNX edge inference.
13. **Cloud deploy?** Docker Compose now; stateless API + Postgres + Redis, CI builds images (`.github/workflows/ci.yml`).
14. **External source fails?** REAL→CACHE→SNAPSHOT→SIM chain; degraded-source badges.
15. **Biggest limitations?** Simplified radio/orbital models, simulated telemetry — see `docs/limitations.md`.
16. **Production changes?** Real probes, 3GPP channels, RL policies, drift monitoring, O-RAN integration.
