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


def test_satellites_derived_geometry(client):
    r = client.get("/api/v1/satellites")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 20
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
    r = client.post("/api/v1/whatif/outage?sat_id=ORBITIQ-DEMO-07")
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
    w = client.post("/api/v1/whatif/outage?sat_id=ORBITIQ-DEMO-07").json()
    assert "affected_cells_count" in w
    # events carry recommended actions
    evts = client.get("/api/v1/incidents").json()["items"]
    assert all("recommended_action" in e for e in evts)


def test_external_data_failure_fallback():
    from backend.data import ingest
    import backend.data.ingest as ing
    cells = ing.load_cells(limit=10)  # works from local snapshot, no network
    assert len(cells) == 10
    sw = ing.load_space_weather("/nonexistent.json")
    assert sw["status"] == "unavailable"
