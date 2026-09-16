# Portfolio Story — ORBITIQ
**PROBLEM**: satellite-to-cellular networks change every second — users move, cells congest, satellites set. Engineers need to see degradation coming and pick the right handoff.
**WHY HARD**: physics (orbits), scale (10k+ devices), uncertainty (noisy telemetry), and trust (every AI call must be explainable).
**APPROACH**: right tool per subproblem — SGP4 physics for geometry, seeded simulation for behavior, RF/IsolationForest for prediction, weighted optimization for ranking, LLM only for explanation.
**REAL DATA**: OpenCelliD + CelesTrak + NOAA, snapshotted, licensed, labeled.
**AI/ML**: honest metrics (F1 0.808, ROC-AUC 0.971), no fake claims, leakage deliberately removed.
**DIGITAL TWIN**: 10,284 devices / 1,500 cells / 24 sats with backend aggregation.
**OPTIMIZATION**: ranked candidates with WHY-deltas; what-if BEFORE/AFTER.
**GENAI**: grounded copilot with refusal guardrails.
**RESULTS**: congestion demo → anomaly → prediction → recommendation → what-if, all reproducible with one command.
**LIMITATIONS**: simplified physics/radio, simulated telemetry — documented, not hidden.
**LEARNED**: credibility comes from provenance, evaluation, and saying what the system can't do.
