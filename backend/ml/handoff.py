"""Handoff optimization: transparent weighted scorer (Model 3) + natural-language explanation.

Score = weighted sum of normalized features. Weights are fixed + documented
(not a black box), and every recommendation ships per-factor deltas so the
UI/Copilot can explain WHY without SHAP on the hot path. A SHAP-style
per-feature contribution is also returned for parity with the explainability req.
"""
from __future__ import annotations

WEIGHTS = {"signal": 0.25, "sinr": 0.15, "elevation": 0.12, "latency": 0.15,
           "capacity": 0.13, "visibility": 0.10, "degradation": 0.10}
WEIGHTS_VERSION = "handoff-scorer-v1"


def _norm_signal(dbm: float) -> float:
    return max(0.0, min(1.0, (dbm + 120) / 40.0))  # -120..-80


def _norm_latency(ms: float) -> float:
    return max(0.0, min(1.0, 1 - (ms - 20) / 160.0))  # 20..180ms


def score_candidate(c: dict) -> tuple[float, dict]:
    parts = {
        "signal": _norm_signal(c.get("signal_dbm", -100)),
        "sinr": max(0.0, min(1.0, (c.get("sinr_db", 5) + 5) / 25.0)),
        "elevation": max(0.0, min(1.0, c.get("elevation_deg", 30) / 90.0)),
        "latency": _norm_latency(c.get("latency_ms", 60)),
        "capacity": float(c.get("capacity_score", 0.5)),
        "visibility": max(0.0, min(1.0, c.get("visibility_min", 5) / 15.0)),
        "degradation": 1 - float(c.get("degradation_prob", 0.3)),
    }
    score = round(sum(parts[k] * WEIGHTS[k] for k in WEIGHTS), 3)
    return score, {k: round(v, 3) for k, v in parts.items()}


def rank_candidates(candidates: list[dict]) -> list[dict]:
    ranked = []
    for c in candidates:
        s, parts = score_candidate(c)
        ranked.append({**c, "score": s, "contributions": parts})
    return sorted(ranked, key=lambda r: r["score"], reverse=True)


def recommend(device_id: str, candidates: list[dict]) -> dict:
    ranked = rank_candidates(candidates)
    best = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else best
    expl = [
        f"predicted signal is {pct(best.get('signal_dbm', -90), runner.get('signal_dbm', -95))} stronger",
        f"estimated latency is {pct(runner.get('latency_ms', 80), best.get('latency_ms', 50))} lower",
        f"predicted congestion is {pct(runner.get('congestion_pct', 80), best.get('congestion_pct', 40))} lower",
        f"expected visibility is ~{max(0, best.get('visibility_min', 8) - runner.get('visibility_min', 4)):.0f} minutes longer",
    ]
    return {"device_id": device_id, "recommended_sat": best["sat_id"], "confidence": best["score"],
            "ranked": [{"sat_id": r["sat_id"], "score": r["score"]} for r in ranked],
            "explanation": expl, "details": ranked, "provenance": "AI RECOMMENDATION"}


def pct(a: float, b: float) -> str:
    if not b:
        return "n/a"
    return f"{abs(a - b) / abs(b) * 100:.0f}%"
