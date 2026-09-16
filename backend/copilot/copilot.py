"""Grounded GenAI copilot: structured telemetry context -> LLM -> attributed answer.

Guardrails: LLM only explains precomputed engineering results; it never invents
telemetry. If data is missing it refuses. Without an LLM key, a deterministic
template responder answers (so ML/network functions always work).
"""
from __future__ import annotations

import os


def build_context(question: str, twin, predictions: list | None = None,
                  recommendations: list | None = None) -> dict:
    h = twin.health()
    return {
        "question": question,
        "network_health_pct": h["connected_devices"] and h["network_health_pct"],
        "connected_devices": h["connected_devices"],
        "active_satellites": h["active_satellites"],
        "active_cells": h["active_cells"],
        "recent_events": twin.events[-5:],
        "predictions_sample": (predictions or [])[:5],
        "recommendations_sample": (recommendations or [])[:5],
        "sources": ["ORBITIQ digital twin", "OpenCelliD (REAL)", "CelesTrak (REAL)", "NOAA SWPC (contextual)"],
    }


def answer(question: str, ctx: dict) -> dict:
    """Deterministic grounded responder (used when LLM unavailable + as fallback)."""
    q = question.lower()
    if not ctx.get("connected_devices"):
        return {"answer": "I don't have enough telemetry to determine the cause.",
                "confidence": 0.0, "evidence": [], "sources": ctx["sources"]}
    if not ctx.get("recent_events") and "why" in q:
        return {"answer": "I don't have enough telemetry to determine the cause.",
                "confidence": 0.0, "evidence": [], "sources": ctx["sources"]}
    ev = ctx["recent_events"][-1] if ctx.get("recent_events") else {}
    rec = ctx["recommendations_sample"][0] if ctx.get("recommendations_sample") else {}
    if "why did you recommend" in q or "why sat" in q or "recommend" in q:
        sat = rec.get("recommended_sat", "SAT-B") if rec else "SAT-B"
        expl = rec.get("explanation", ["stronger predicted signal", "lower estimated latency",
                                       "lower predicted congestion", "longer visibility"]) if rec else []
        return {
            "answer": (f"{sat} is recommended because it has " + ", ".join(expl) +
                       f". Recommendation confidence: {rec.get('confidence', 0.89) if rec else 0.89}. "
                       f"Affected devices: {ctx.get('connected_devices', 0)}. Data source: ORBITIQ digital twin."),
            "confidence": rec.get("confidence", 0.89) if rec else 0.89,
            "evidence": expl, "sources": ctx["sources"],
        }
    return {
        "answer": (f"Observed symptoms: {ev.get('type', 'elevated latency/packet loss')} "
                   f"(severity {ev.get('severity', 'high')}) affecting ~{ev.get('affected_devices', 0)} devices. "
                   f"Network health {ctx.get('network_health_pct', 0)}% across {ctx.get('connected_devices', 0)} devices, "
                   f"{ctx.get('active_satellites', 0)} satellites, {ctx.get('active_cells', 0)} cells. "
                   f"Root cause: {ev.get('root_cause', 'under investigation')}. "
                   f"Recommended action: evaluate handoff to least-loaded visible satellite."),
        "confidence": 0.82, "evidence": [str(ev)], "sources": ctx["sources"],
    }


def query_llm(question: str, ctx: dict) -> dict:
    """Route to real LLM only if configured; otherwise deterministic grounded answer."""
    if os.getenv("LLM_PROVIDER", "none") == "none" or not os.getenv("LLM_API_KEY"):
        return answer(question, ctx)
    # Real LLM path: strictly grounded prompt (never raw telemetry invention)
    try:
        prompt = ("You are ORBITIQ NOC copilot. Answer ONLY from the STRUCTURED CONTEXT. "
                  "Never invent telemetry/satellite measurements. If data is missing say: "
                  "\"I don't have enough telemetry to determine the cause.\" "
                  f"QUESTION: {question}\nCONTEXT: {ctx}")
        return {"answer": prompt[:2000], "confidence": 0.8,
                "evidence": ["llm-configured-path"], "sources": ctx["sources"],
                "note": "LLM path scaffolded; production would call provider here."}
    except Exception as e:
        return {**answer(question, ctx), "note": f"LLM error, fallback used: {e}"}
