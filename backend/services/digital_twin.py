"""Digital-twin service: owns cells, satellites, devices, aggregation (never ships raw 10k to browser)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from backend.data.ingest import load_cells, load_tles
from backend.satellite.propagate import (
    ground_geometry,
    propagate_tle,
    visibility_duration_minutes,
)
from backend.simulation.devices import DeviceSimulator
from backend.simulation.events import demo_congestion_scenario

log = logging.getLogger("orbitiq.twin")


class DigitalTwin:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.cells: list[dict] = []
        self.tles: list[tuple[str, str, str]] = []
        self.sim = DeviceSimulator(seed=seed)
        self.events: list[dict] = []
        self.sat_util: dict[str, float] = {}
        self.loaded = False

    def load(self, n_cells: int = 1500, n_devices: int = 10284) -> dict:
        # Fresh state on every (re)load — never accumulate across demo/reset calls.
        self.sim.devices.clear()
        self.events.clear()
        self.sat_util.clear()
        self.cells = load_cells(limit=n_cells)
        self.tles = load_tles()
        self.sim.spawn(n_devices)
        # attach nearest cell + round-robin satellite
        for i, d in enumerate(self.sim.devices.values()):
            d.serving_cell = self.cells[i % len(self.cells)]["cell_id"] if self.cells else None
            d.serving_satellite = self.tles[i % len(self.tles)][0] if self.tles else None
            d.candidate_cells = [self.cells[(i + k) % len(self.cells)]["cell_id"] for k in (1, 2, 3)] if self.cells else []
            d.candidate_satellites = [self.tles[(i + k) % len(self.tles)][0] for k in (1, 2, 3)] if self.tles else []
        for name, _, _ in self.tles:
            self.sat_util[name] = 0.55
        self.loaded = True
        return self.health()

    def health(self) -> dict:
        degraded = sum(1 for d in self.sim.devices.values() if d.latency_ms > 100 or d.packet_loss_pct > 2.0)
        total = max(1, len(self.sim.devices))
        return {
            "connected_devices": len(self.sim.devices),
            "active_satellites": len(self.tles),
            "active_cells": len(self.cells),
            "network_health_pct": round(100 * (1 - degraded / total), 1),
            "predicted_incidents": sum(1 for e in self.events if e["severity"] in ("high", "critical")),
            "ai_recommendations": len(self.events),
        }

    def satellite_states(self, gs_lat: float = 37.7749, gs_lon: float = -122.4194,
                           limit: Optional[int] = None) -> list[dict]:
        now = datetime.now(timezone.utc)
        out = []
        tles = self.tles[:limit] if limit else self.tles
        for name, l1, l2 in tles:
            try:
                fix = propagate_tle(name, l1, l2, now)
                g = ground_geometry(fix.lat, fix.lon, fix.altitude_km, gs_lat, gs_lon)
                out.append({"sat_id": name, "name": name, "lat": fix.lat, "lon": fix.lon,
                            "altitude_km": fix.altitude_km, **g,
                            "visibility_duration_min": visibility_duration_minutes(name, l1, l2, gs_lat, gs_lon, now),
                            "utilization_pct": round(self.sat_util.get(name, 0.55) * 100, 1),
                            "provenance_position": "REAL", "provenance_geometry": "DERIVED"})
            except Exception as e:
                log.warning("satellite state failed for %s: %s", name, e)
                continue
        return out

    def inject_congestion(self, sat_id: str | None = None, util: float = 0.94) -> list[dict]:
        target = sat_id or (self.tles[7][0] if len(self.tles) > 7 else self.tles[0][0])
        self.sat_util[target] = util
        alt = self.tles[11][0] if len(self.tles) > 11 else (self.tles[1][0] if len(self.tles) > 1 else target)
        new_events = demo_congestion_scenario(sats=[target, alt])
        # stamp the scenario with live twin counts (never stale hardcodes)
        on_target = sum(1 for d in self.sim.devices.values() if d.serving_satellite == target)
        for i, e in enumerate(new_events):
            e["affected_devices"] = on_target if i == 0 else int(on_target * 0.85)
        self.events.extend(new_events)
        # push telemetry effect: step sim under load so metrics actually move.
        # 8 steps lets EMA telemetry converge toward the congested regime,
        # so the incident is visible in the twin (not just declared).
        # Congestion is targeted: only devices served by this satellite suffer.
        for _ in range(8):
            self.sim.step(dt_s=60, congestion={"sat_id": target, "sat_util": util,
                                               "nominal_sat_util": 0.55, "cell_util": 0.62})
        return self.events

    def grid_aggregation(self, resolution: float = 0.1) -> list[dict]:
        """Geographic clustering for map: aggregate devices into grid cells."""
        buckets: dict[tuple[float, float], dict] = {}
        for d in self.sim.devices.values():
            key = (round(d.lat / resolution) * resolution, round(d.lon / resolution) * resolution)
            b = buckets.setdefault(key, {"lat": key[0], "lon": key[1], "count": 0,
                                         "lat_sum": 0.0, "loss_sum": 0.0, "degraded": 0})
            b["count"] += 1
            b["lat_sum"] += d.latency_ms
            b["loss_sum"] += d.packet_loss_pct
            if d.latency_ms > 100 or d.packet_loss_pct > 2.0:
                b["degraded"] += 1
        return [{"lat": v["lat"], "lon": v["lon"], "count": v["count"],
                 "avg_latency_ms": round(v["lat_sum"] / v["count"], 1),
                 "avg_loss_pct": round(v["loss_sum"] / v["count"], 2),
                 "degraded": v["degraded"]} for v in buckets.values()]

    def topology(self, limit_devices: int = 50) -> dict:
        nodes, links = [], []
        for name, _, _ in self.tles[:12]:
            nodes.append({"id": name, "type": "satellite"})
        for c in self.cells[:20]:
            nodes.append({"id": c["cell_id"], "type": "cell"})
            links.append({"from": c["cell_id"], "to": "GS-SFO-01", "rel": "ROUTES_THROUGH"})
        nodes.append({"id": "GS-SFO-01", "type": "ground_station"})
        devs = list(self.sim.devices.values())[:limit_devices]
        for d in devs:
            nodes.append({"id": d.device_id, "type": "device"})
            if d.serving_cell:
                links.append({"from": d.device_id, "to": d.serving_cell, "rel": "CONNECTED_TO"})
            if d.serving_satellite:
                links.append({"from": d.device_id, "to": d.serving_satellite, "rel": "VISIBLE_TO"})
        return {"nodes": nodes, "links": links[:400]}


# Process-wide singleton (demo scale; Postgres persistence is additive)
TWIN = DigitalTwin(seed=42)
