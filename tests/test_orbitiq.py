import os

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/orbitiq_test.db")

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").status_code == 200


def test_network_health_provenance(client):
    r = client.get("/api/v1/network/health")
    assert r.status_code == 200
    body = r.json()
    assert body["connected_devices"] >= 10000
    assert body["active_cells"] >= 1000
    assert "provenance" in body


def test_cells_real_attribution(client):
    r = client.get("/api/v1/cells?limit=5")
    assert r.status_code == 200
    assert "OpenCelliD" in r.json()["attribution"]


def _live_sat_id(client, idx: int = 7) -> str:
    """Resolve a real satellite ID from the twin (live or snapshot names)."""
    items = client.get("/api/v1/satellites").json()["items"]
    return items[min(idx, len(items) - 1)]["sat_id"]


def test_satellites_derived_geometry(client):
    r = client.get("/api/v1/satellites")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 10  # live CelesTrak groups vary; snapshot ships 24
    s = items[0]
    assert -90 <= s["lat"] <= 90 and s["altitude_km"] > 100
    assert "elevation_deg" in s and "slant_range_km" in s


def test_predictions_have_probabilities(client):
    r = client.get("/api/v1/predictions?limit=50")
    assert r.status_code == 200
    for p in r.json()["items"]:
        assert 0.0 <= p["probability"] <= 1.0


def test_recommendation_explainable(client):
    r = client.get("/api/v1/recommendations")
    assert r.status_code == 200
    body = r.json()
    assert body["recommended_sat"]
    assert len(body["explanation"]) >= 3
    assert len(body["ranked"]) >= 2


def test_whatif_before_after(client):
    sat_id = _live_sat_id(client)
    r = client.post(f"/api/v1/whatif/outage?sat_id={sat_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["before"]["degraded_users"] >= body["after_ai_optimization"]["degraded_users"]
    assert body["provenance"] == "SIMULATION RESULT"


def test_copilot_grounded_refusal():
    from backend.copilot.copilot import answer
    out = answer("why is latency high?", {"question": "x", "recent_events": [],
                                          "sources": ["twin"], "connected_devices": 0})
    assert "don't have enough telemetry" in out["answer"]


def test_copilot_no_hallucination(client):
    r = client.post("/api/v1/copilot/query", json={"question": "Why did you recommend this satellite?"})
    assert r.status_code == 200
    assert "sources" in r.json()


def test_simulation_deterministic():
    from backend.simulation.devices import DeviceSimulator
    a, b = DeviceSimulator(seed=42), DeviceSimulator(seed=42)
    a.spawn(50)
    b.spawn(50)
    assert [d.lat for d in a.step()] == [d.lat for d in b.step()]


def test_satellite_visibility_math():
    from backend.satellite.propagate import ground_geometry
    g = ground_geometry(37.8, -122.4, 550, 37.7749, -122.4194)
    assert g["visible"] is True and g["elevation_deg"] > 10
    g2 = ground_geometry(-37.8, 57.6, 550, 37.7749, -122.4194)
    assert g2["visible"] is False


def test_satellite_tracks_shape(client):
    r = client.get("/api/v1/satellites/tracks?minutes=10&step_s=120")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 10
    t0 = body["tracks"][0]
    assert len(t0["path"]) == 11  # -10..+10 min at 120 s steps
    lon, lat = t0["path"][0]
    assert -180 <= lon <= 180 and -90 <= lat <= 90


def test_api_surface_sweep(client):
    """Exercise remaining endpoints so coverage reflects the real surface."""
    assert client.get("/api/v1/devices?limit=5").status_code == 200
    assert client.get("/api/v1/coverage").status_code == 200
    assert client.get("/api/v1/telemetry?limit=5").status_code == 200
    assert client.get("/api/v1/telemetry?device_id=dev-00001").status_code == 200
    assert client.get("/api/v1/space-weather").status_code == 200
    assert client.get("/api/v1/network/topology").status_code == 200
    assert client.get("/api/v1/demo/status").status_code == 200
    r = client.post("/api/v1/recommendations", json={"device_id": "dev-00002"})
    assert r.status_code == 200 and r.json()["recommended_sat"]
    r = client.post("/api/v1/recommendations", json={
        "device_id": "dev-00003",
        "candidates": [{"sat_id": "S-A", "signal_dbm": -90, "latency_ms": 60},
                       {"sat_id": "S-B", "signal_dbm": -85, "latency_ms": 40}]})
    assert r.json()["recommended_sat"] == "S-B"
    r = client.post("/api/v1/copilot/query", json={"question": "Why are users slow?"})
    assert r.status_code == 200 and "sources" in r.json()
    r = client.post("/api/v1/demo/start", json={"n_devices": 500})
    assert r.status_code == 200
    r = client.post("/api/v1/demo/reset")
    assert r.status_code == 200
    # anomaly items now carry affected_area
    a = client.get("/api/v1/anomalies?limit=10").json()["items"]
    assert all("affected_area" in x for x in a)
    # device snapshot carries full telemetry fields
    d = client.get("/api/v1/devices?limit=1").json()["items"][0]
    for k in ("rsrq_db", "signal_strength_dbm", "candidate_cells", "candidate_satellites"):
        assert k in d, k
    # what-if carries affected cells
    w = client.post(f"/api/v1/whatif/outage?sat_id={_live_sat_id(client)}").json()
    assert "affected_cells_count" in w
    # events carry recommended actions
    evts = client.get("/api/v1/incidents").json()["items"]
    assert all("recommended_action" in e for e in evts)


def test_congestion_is_targeted(client):
    """Congestion degrades only the target satellite's users (not the fleet)."""
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/simulation/run", json={"scenario": "satellite_congestion"})
    h = client.get("/api/v1/network/health").json()
    assert 90.0 < h["network_health_pct"] < 100.0
    assert h["predicted_incidents"] >= 1
    client.post("/api/v1/demo/reset")


def test_decisions_persist_to_db(client):
    """Decisions/events land in normalized tables (SQLite fallback in tests)."""
    from backend.models import db as models
    from backend.models.session import SessionLocal
    client.post("/api/v1/simulation/run", json={"scenario": "satellite_congestion"})
    client.get("/api/v1/recommendations")
    client.get("/api/v1/predictions?limit=20")
    db = SessionLocal()
    try:
        assert db.query(models.Event).count() >= 3
        assert db.query(models.Recommendation).count() >= 1
        assert db.query(models.Prediction).count() >= 1
        assert db.query(models.Cell).count() >= 1000
        assert db.query(models.Satellite).count() >= 20
        assert db.query(models.DataSource).count() >= 4
    finally:
        db.close()
    client.post("/api/v1/demo/reset")


def test_api_contracts_match_schemas(client):
    """Endpoint payloads validate against the shared Pydantic schemas."""
    from backend.models.schemas import CellSite, DeviceTelemetry, SatelliteState
    cells = client.get("/api/v1/cells?limit=5").json()["items"]
    assert [CellSite(**c).cell_id for c in cells]
    sats = client.get("/api/v1/satellites").json()["items"][:5]
    assert [SatelliteState(**s).sat_id for s in sats]
    devs = client.get("/api/v1/devices?limit=5").json()["items"]
    assert [DeviceTelemetry(**d).device_id for d in devs]


def test_external_data_failure_fallback():
    import backend.data.ingest as ing
    cells = ing.load_cells(limit=10)  # works from local snapshot, no network
    assert len(cells) == 10
    sw = ing.load_space_weather("/nonexistent.json")
    assert sw["status"] == "unavailable"
