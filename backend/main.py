"""ORBITIQ FastAPI backend — versioned APIs over the digital twin + ML + copilot."""
from __future__ import annotations
import logging
import time
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.config import get_settings
from backend.services.digital_twin import TWIN
from backend.services.whatif import run_outage_scenario
from backend.copilot.copilot import build_context, query_llm
from backend.data.ingest import load_space_weather

log = logging.getLogger("orbitiq.api")
settings = get_settings()
app = FastAPI(title="ORBITIQ API",
              description="Independent engineering research prototype inspired by satellite-to-cellular challenges. No proprietary SpaceX data.",
              version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

LAST_RECS: list[dict] = []
LAST_PREDS: list[dict] = []


def _ensure_loaded() -> None:
    if not TWIN.loaded:
        TWIN.load(n_cells=1500, n_devices=settings.demo_devices)


@app.middleware("http")
async def _lazy_load_twin(request: Request, call_next):
    if request.url.path.startswith("/api/") and not TWIN.loaded:
        try:
            _ensure_loaded()
        except Exception as e:
            log.warning("lazy twin load failed: %s", e)
    return await call_next(request)


@app.on_event("startup")
def _startup():
    logging.basicConfig(level=settings.log_level)
    if not TWIN.loaded:
        TWIN.load(n_cells=1500, n_devices=settings.demo_devices)
    log.info("ORBITIQ twin ready: %s", TWIN.health())


@app.get("/health")
def health():
    return {"status": "ok", "service": "orbitiq-backend"}


@app.get("/ready")
def ready():
    base: dict = {"ready": TWIN.loaded}
    if TWIN.loaded:
        base.update(TWIN.health())
    return base


# ---------------- v1 ----------------
@app.get("/api/v1/network/health")
def network_health():
    return {**TWIN.health(), "provenance": {"devices": "SIMULATED", "cells": "REAL(OpenCelliD)", "satellites": "REAL(CelesTrak)"}}


@app.get("/api/v1/cells")
def cells(limit: int = Query(200, le=2000), offset: int = 0):
    return {"items": TWIN.cells[offset:offset + limit], "total": len(TWIN.cells),
            "attribution": "Cellular infrastructure data: OpenCelliD (CC BY-SA 4.0)", "provenance": "REAL"}


@app.get("/api/v1/satellites")
def satellites(gs_lat: float = 37.7749, gs_lon: float = -122.4194):
    t0 = time.time()
    states = TWIN.satellite_states(gs_lat, gs_lon)
    return {"items": states, "count": len(states),
            "attribution": "Orbital data: CelesTrak (public TLE, SGP4)",
            "provenance": "REAL position + DERIVED geometry",
            "inference_ms": round((time.time() - t0) * 1000, 1)}


@app.get("/api/v1/devices")
def devices(limit: int = Query(200, le=2000)):
    return {"items": TWIN.sim.snapshot(limit), "total": len(TWIN.sim.devices), "provenance": "SIMULATED"}


@app.get("/api/v1/coverage")
def coverage(resolution: float = 0.1):
    return {"grid": TWIN.grid_aggregation(resolution), "provenance": "SIMULATED aggregation"}


@app.get("/api/v1/incidents")
def incidents():
    return {"items": TWIN.events, "count": len(TWIN.events)}


@app.get("/api/v1/telemetry")
def telemetry(device_id: Optional[str] = None, limit: int = 200):
    rows = TWIN.sim.snapshot(limit)
    if device_id:
        rows = [r for r in rows if r["device_id"] == device_id]
    return {"items": rows, "provenance": "SIMULATED"}


@app.get("/api/v1/network/topology")
def topology():
    return {**TWIN.topology(), "provenance": "REAL infra + SIMULATED devices + DERIVED links"}


@app.get("/api/v1/space-weather")
def space_weather():
    return {**load_space_weather(), "provenance": "REAL (contextual only — not a performance predictor)"}


@app.get("/api/v1/predictions")
def predictions(limit: int = 200):
    from backend.ml.degradation import predict_degradation
    rows = TWIN.sim.snapshot(limit)
    try:
        preds = predict_degradation([{"device_id": r["device_id"], "latency_ms": r["latency_ms"],
                                      "packet_loss_pct": r["packet_loss_pct"], "throughput_mbps": r["throughput_mbps"],
                                      "rsrp_dbm": r["rsrp_dbm"], "sinr_db": r["sinr_db"],
                                      "jitter_ms": r.get("jitter_ms", 5.0),
                                      "velocity_ms": r.get("velocity_ms", 8.0)} for r in rows])
    except Exception as e:
        raise HTTPException(503, f"model unavailable: {e}")
    global LAST_PREDS
    LAST_PREDS = preds
    degraded = sum(1 for p in preds if p["probability"] > 0.5)
    return {"items": preds, "degraded_count": degraded, "horizon_min": 5, "provenance": "PREDICTION"}


@app.get("/api/v1/anomalies")
def anomalies(limit: int = 200):
    from backend.ml.anomaly import score_anomaly
    rows = TWIN.sim.snapshot(limit)
    try:
        out = score_anomaly([{"device_id": r["device_id"], "lat": r["lat"], "lon": r["lon"],
                              "latency_ms": r["latency_ms"],
                              "packet_loss_pct": r["packet_loss_pct"], "throughput_mbps": r["throughput_mbps"],
                              "rsrp_dbm": r["rsrp_dbm"], "sinr_db": r["sinr_db"],
                              "jitter_ms": r.get("jitter_ms", 5.0)} for r in rows])
    except Exception as e:
        raise HTTPException(503, f"model unavailable: {e}")
    return {"items": out, "anomaly_count": sum(1 for o in out if o["severity"] != "normal"),
            "provenance": "PREDICTION"}


class HandoffRequest(BaseModel):
    device_id: str
    candidates: Optional[list[dict]] = None


@app.get("/api/v1/recommendations")
def recommendations(device_id: str = "dev-00001"):
    from backend.ml.handoff import recommend
    sats = TWIN.satellite_states()[:3]
    cands = [{"sat_id": s["sat_id"], "signal_dbm": -88 + i * 4, "sinr_db": 8 + i * 2,
              "elevation_deg": s.get("elevation_deg") or 35, "slant_range_km": s.get("slant_range_km") or 800,
              "latency_ms": 55 - i * 8, "capacity_score": 0.6 + i * 0.12,
              "visibility_min": s.get("visibility_duration_min") or 6,
              "congestion_pct": s.get("utilization_pct", 60) - i * 15,
              "degradation_prob": 0.3 - i * 0.08} for i, s in enumerate(sats)]
    rec = recommend(device_id, cands)
    global LAST_RECS
    LAST_RECS = [rec]
    return rec


@app.post("/api/v1/recommendations")
def recommend_post(req: HandoffRequest):
    from backend.ml.handoff import recommend
    cands = req.candidates or []
    if not cands:
        return recommendations(req.device_id)
    return recommend(req.device_id, cands)


class SimRequest(BaseModel):
    scenario: str = "satellite_congestion"
    sat_id: Optional[str] = None


@app.post("/api/v1/simulation/run")
def simulation_run(req: SimRequest):
    if req.scenario == "satellite_congestion":
        evts = TWIN.inject_congestion(req.sat_id)
        return {"events": evts, "health": TWIN.health(), "provenance": "SIMULATION RESULT"}
    raise HTTPException(400, f"unknown scenario {req.scenario}")


@app.post("/api/v1/whatif/outage")
def whatif_outage(sat_id: str = "ORBITIQ-DEMO-07"):
    return run_outage_scenario(TWIN, sat_id)


class CopilotRequest(BaseModel):
    question: str


@app.post("/api/v1/copilot/query")
def copilot_query(req: CopilotRequest):
    ctx = build_context(req.question, TWIN, LAST_PREDS, LAST_RECS)
    return {**query_llm(req.question, ctx), "provenance": "GROUNDED IN DIGITAL-TWIN TELEMETRY"}


class DemoRequest(BaseModel):
    n_devices: int = 10284


@app.post("/api/v1/demo/start")
def demo_start(req: Optional[DemoRequest] = None):
    TWIN.load(n_cells=1500, n_devices=(req.n_devices if req else settings.demo_devices))
    evts = TWIN.inject_congestion()
    return {"health": TWIN.health(), "events": [e["event_id"] for e in evts], "steps": [
        "real cellular infrastructure loaded", "orbital data loaded", "satellite visibility computed",
        "simulated devices started", "satellite congestion introduced", "anomaly detected",
        "degradation predicted", "handoff recommended", "what-if ready", "copilot ready"]}


@app.get("/api/v1/demo/status")
def demo_status():
    return {"loaded": TWIN.loaded, **TWIN.health()}


@app.post("/api/v1/demo/reset")
def demo_reset():
    TWIN.events.clear()
    TWIN.load(n_cells=1500, n_devices=settings.demo_devices)
    LAST_RECS.clear()
    LAST_PREDS.clear()
    return {"reset": True, "health": TWIN.health()}


@app.get("/api/v1/demo/recruiter-script")
def recruiter_script():
    """Deterministic 12-step ~3-minute recruiter narration."""
    return {"steps": [
        {"t": 0, "title": "Real cellular infrastructure appears", "action": "GET /api/v1/cells"},
        {"t": 15, "title": "Satellite trajectories appear", "action": "GET /api/v1/satellites"},
        {"t": 30, "title": "10,000+ simulated devices appear", "action": "GET /api/v1/coverage"},
        {"t": 50, "title": "Introduce satellite congestion", "action": "POST /api/v1/simulation/run"},
        {"t": 70, "title": "AI detects anomaly", "action": "GET /api/v1/anomalies"},
        {"t": 90, "title": "AI predicts connectivity degradation", "action": "GET /api/v1/predictions"},
        {"t": 110, "title": "AI recommends alternative satellite", "action": "GET /api/v1/recommendations"},
        {"t": 130, "title": "Show explainability", "action": "see recommendations.explanation"},
        {"t": 145, "title": "Run outage what-if", "action": "POST /api/v1/whatif/outage"},
        {"t": 160, "title": "Show before/after", "action": "see whatif.before vs after_ai_optimization"},
        {"t": 170, "title": 'Ask Copilot: "Why did you recommend this satellite?"', "action": "POST /api/v1/copilot/query"},
        {"t": 180, "title": "Show data provenance", "action": "GET /api/v1/network/health + data_sources.yaml"},
    ]}


@app.get("/", response_class=HTMLResponse)
def root():
    return """<html><body style="font-family:sans-serif;background:#0b1220;color:#e5e7eb;padding:40px">
    <h1>ORBITIQ</h1><p>AI-Powered Satellite-to-Cellular Network Intelligence (independent research prototype).</p>
    <p><a style="color:#7dd3fc" href="/docs">OpenAPI docs</a> | <a style="color:#7dd3fc" href="/api/v1/network/health">network health</a></p>
    <p style="color:#94a3b3">ORBITIQ is an independent engineering research prototype inspired by the technical challenges
    of satellite-to-cellular connectivity. It uses public datasets, derived engineering features, and controlled
    simulation. It does not use proprietary SpaceX data.</p></body></html>"""
