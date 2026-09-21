"""ORBITIQ FastAPI backend — versioned APIs over the digital twin + ML + copilot."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.config import get_settings
from backend.copilot.copilot import build_context, query_llm
from backend.data.ingest import load_cells, load_space_weather, load_tles
from backend.models import db as models
from backend.models.session import SessionLocal, init_db
from backend.services.digital_twin import TWIN
from backend.services.whatif import run_outage_scenario

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
        _seed_reference_data()


def _save(instances: list) -> None:
    """Best-effort persistence: the twin stays authoritative in memory;
    Postgres (or the SQLite fallback) keeps decisions, events, and runs."""
    if not instances:
        return
    try:
        db = SessionLocal()
        try:
            db.add_all(instances)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        log.warning("persist skipped (non-fatal): %s", e)


def _seed_reference_data() -> None:
    """Seed reference tables once: cells, satellites, data-source registry."""
    try:
        db = SessionLocal()
        try:
            if db.query(models.Cell).count() == 0:
                for c in load_cells(limit=1500):
                    db.add(models.Cell(cell_id=c["cell_id"], mcc=c["mcc"], mnc=c["mnc"],
                                       tac=c["tac"], radio=c["radio"], lat=c["lat"],
                                       lon=c["lon"], range_m=c["range_m"], samples=c["samples"]))
            if db.query(models.Satellite).count() == 0:
                for name, l1, l2 in load_tles():
                    db.add(models.Satellite(sat_id=name, name=name, tle_line1=l1, tle_line2=l2))
            if db.query(models.DataSource).count() == 0:
                for key, source, dtype, lic, cls in [
                    ("opencellid", "OpenCelliD", "real", "CC BY-SA 4.0", "REAL"),
                    ("celestrak", "CelesTrak", "public orbital data", "public domain", "REAL"),
                    ("noaa_swpc", "NOAA SWPC", "public space-weather data", "US public domain", "REAL"),
                    ("orbitiq_sim", "ORBITIQ simulator", "simulated", "n/a", "SIMULATED"),
                ]:
                    db.add(models.DataSource(key=key, source=source, type=dtype,
                                             license=lic, classification=cls))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        log.warning("reference seed skipped (non-fatal): %s", e)


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
    try:
        init_db()
    except Exception as e:
        log.warning("init_db skipped (non-fatal): %s", e)
    if not TWIN.loaded:
        TWIN.load(n_cells=1500, n_devices=settings.demo_devices)
        _seed_reference_data()
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
def cells(limit: int = Query(200, ge=1, le=2000), offset: int = Query(0, ge=0)):
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


@app.get("/api/v1/satellites/tracks")
def satellite_tracks(minutes: int = Query(30, ge=5, le=60), step_s: int = Query(60, ge=30, le=300)):
    t0 = time.time()
    tracks = TWIN.satellite_tracks(minutes=minutes, step_s=step_s)
    return {"tracks": tracks, "count": len(tracks),
            "attribution": "Orbital data: CelesTrak (public TLE, SGP4)",
            "provenance": "REAL position + DERIVED ground tracks",
            "compute_ms": round((time.time() - t0) * 1000, 1)}


@app.get("/api/v1/devices")
def devices(limit: int = Query(200, ge=1, le=2000)):
    return {"items": TWIN.sim.snapshot(limit), "total": len(TWIN.sim.devices), "provenance": "SIMULATED"}


@app.get("/api/v1/coverage")
def coverage(resolution: float = 0.1):
    return {"grid": TWIN.grid_aggregation(resolution), "provenance": "SIMULATED aggregation"}


@app.get("/api/v1/incidents")
def incidents():
    return {"items": TWIN.events, "count": len(TWIN.events)}


@app.get("/api/v1/telemetry")
def telemetry(device_id: Optional[str] = None, limit: int = Query(200, ge=1, le=2000)):
    if device_id:
        # direct lookup across the full fleet (not just the first `limit` rows)
        rows = TWIN.sim.snapshot(len(TWIN.sim.devices))
        rows = [r for r in rows if r["device_id"] == device_id]
    else:
        rows = TWIN.sim.snapshot(limit)
    return {"items": rows, "provenance": "SIMULATED"}


@app.get("/api/v1/network/topology")
def topology():
    return {**TWIN.topology(), "provenance": "REAL infra + SIMULATED devices + DERIVED links"}


@app.get("/api/v1/space-weather")
def space_weather():
    return {**load_space_weather(), "provenance": "REAL (contextual only — not a performance predictor)"}


@app.get("/api/v1/predictions")
def predictions(limit: int = Query(200, ge=1, le=2000)):
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
    _save([models.Prediction(device_id=p["device_id"] or "", probability=p["probability"],
                             confidence=p["confidence"], horizon_min=5)
           for p in preds[:100]])  # bounded history sample, not the full poll
    return {"items": preds, "degraded_count": degraded, "horizon_min": 5, "provenance": "PREDICTION"}


@app.get("/api/v1/anomalies")
def anomalies(limit: int = Query(200, ge=1, le=2000)):
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
    sats = TWIN.satellite_states(limit=3)
    cands = [{"sat_id": s["sat_id"], "signal_dbm": -88 + i * 4, "sinr_db": 8 + i * 2,
              "elevation_deg": s.get("elevation_deg") or 35, "slant_range_km": s.get("slant_range_km") or 800,
              "latency_ms": 55 - i * 8, "capacity_score": 0.6 + i * 0.12,
              "visibility_min": s.get("visibility_duration_min") or 6,
              "congestion_pct": s.get("utilization_pct", 60) - i * 15,
              "degradation_prob": 0.3 - i * 0.08} for i, s in enumerate(sats)]
    rec = recommend(device_id, cands)
    global LAST_RECS
    LAST_RECS = [rec]
    _save([models.Recommendation(device_id=device_id, recommended_sat=rec["recommended_sat"],
                                 confidence=rec["confidence"],
                                 explanation={"points": rec["explanation"]})])
    return rec


@app.post("/api/v1/recommendations")
def recommend_post(req: HandoffRequest):
    from backend.ml.handoff import recommend
    cands = req.candidates or []
    if not cands:
        return recommendations(req.device_id)
    rec = recommend(req.device_id, cands)
    _save([models.Recommendation(device_id=req.device_id, recommended_sat=rec["recommended_sat"],
                                 confidence=rec["confidence"],
                                 explanation={"points": rec["explanation"]})])
    return rec


class SimRequest(BaseModel):
    scenario: str = "satellite_congestion"
    sat_id: Optional[str] = None


@app.post("/api/v1/simulation/run")
def simulation_run(req: SimRequest):
    if req.scenario == "satellite_congestion":
        evts = TWIN.inject_congestion(req.sat_id)
        _save([models.Event(event_id=e["event_id"],
                            timestamp=datetime.fromisoformat(e["timestamp"]),
                            type=e["type"], severity=e["severity"],
                            lat=e["location"]["lat"], lon=e["location"]["lon"],
                            meta={"root_cause": e["root_cause"],
                                  "affected_devices": e["affected_devices"],
                                  "affected_satellites": e["affected_satellites"]})
               for e in evts])
        return {"events": evts, "health": TWIN.health(), "provenance": "SIMULATION RESULT"}
    raise HTTPException(400, f"unknown scenario {req.scenario}")


@app.post("/api/v1/whatif/outage")
def whatif_outage(sat_id: Optional[str] = None):
    target = sat_id or (TWIN.tles[7][0] if len(TWIN.tles) > 7 else TWIN.tles[0][0])
    return run_outage_scenario(TWIN, target)


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
    health = TWIN.health()
    _save([models.SimulationRun(run_id=f"run-{uuid.uuid4().hex[:8]}", seed=settings.simulation_seed,
                                n_devices=health["connected_devices"], scenario="demo",
                                summary=health)])
    return {"health": health, "events": [e["event_id"] for e in evts], "steps": [
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
    health = TWIN.health()
    _save([models.SimulationRun(run_id=f"run-{uuid.uuid4().hex[:8]}", seed=settings.simulation_seed,
                                n_devices=health["connected_devices"], scenario="reset",
                                summary=health)])
    return {"reset": True, "health": health}


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
