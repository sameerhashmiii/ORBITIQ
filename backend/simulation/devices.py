"""Deterministic mobile-device simulator with temporally-consistent mobility.

Mobility profiles: stationary | urban | highway | rural | train | random_walk.
State evolves via seeded RNG (SIMULATION_SEED) — no independent random jumps.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

PROFILES = {
    "stationary": {"speed_ms": 0.0, "turn_deg": 0.0},
    "urban": {"speed_ms": 8.0, "turn_deg": 35.0},
    "highway": {"speed_ms": 28.0, "turn_deg": 4.0},
    "rural": {"speed_ms": 15.0, "turn_deg": 10.0},
    "train": {"speed_ms": 45.0, "turn_deg": 1.5},
    "random_walk": {"speed_ms": 1.5, "turn_deg": 90.0},
}

METERS_PER_DEG_LAT = 111320.0


@dataclass
class Device:
    device_id: str
    lat: float
    lon: float
    velocity_ms: float
    direction_deg: float
    profile: str = "urban"
    battery_pct: float = 80.0
    serving_cell: str | None = None
    serving_satellite: str | None = None
    candidate_cells: list = field(default_factory=list)
    candidate_satellites: list = field(default_factory=list)
    # smoothed radio state (temporal continuity via EMA)
    rsrp_dbm: float = -100.0
    rsrq_db: float = -12.0
    signal_strength_dbm: float = -100.0
    sinr_db: float = 6.0
    latency_ms: float = 45.0
    packet_loss_pct: float = 0.4
    throughput_mbps: float = 30.0
    jitter_ms: float = 5.0


class DeviceSimulator:
    def __init__(self, seed: int = 42, center: tuple[float, float] = (37.7749, -122.4194)):
        # Seeded PRNG is required: the simulator must be deterministic (SIMULATION_SEED).
        self.rng = random.Random(seed)  # noqa: S311 - deterministic simulation, not crypto
        self.center = center
        self.devices: dict[str, Device] = {}

    def spawn(self, n: int, profile_mix: dict[str, float] | None = None) -> list[Device]:
        profile_mix = profile_mix or {"urban": 0.45, "stationary": 0.2, "highway": 0.12,
                                      "rural": 0.1, "train": 0.03, "random_walk": 0.1}
        profiles = list(profile_mix.keys())
        weights = list(profile_mix.values())
        for i in range(n):
            p = self.rng.choices(profiles, weights)[0]
            lat = self.rng.gauss(self.center[0], 0.30)
            lon = self.rng.gauss(self.center[1], 0.35)
            dev = Device(
                device_id=f"dev-{len(self.devices):05d}",
                lat=lat, lon=lon,
                velocity_ms=PROFILES[p]["speed_ms"] * self.rng.uniform(0.7, 1.3),
                direction_deg=self.rng.uniform(0, 360),
                profile=p,
                battery_pct=self.rng.uniform(20, 100),
                rsrp_dbm=self.rng.uniform(-115, -85),
                sinr_db=self.rng.uniform(-2, 18),
            )
            self.devices[dev.device_id] = dev
        return list(self.devices.values())

    def step(self, dt_s: float = 30.0, congestion: dict | None = None) -> list[Device]:
        """Advance all devices one timestep with EMA-smoothed telemetry.

        `congestion` may target one satellite ({sat_id, sat_util}) while the
        rest of the fleet stays at `nominal_sat_util` — congestion is local,
        not global. Without `sat_id`, `sat_util` applies uniformly (training).
        """
        congestion = congestion or {}
        hot_sat = congestion.get("sat_id")
        hot_load = congestion.get("sat_util", 0.6)
        nominal_load = congestion.get("nominal_sat_util", hot_load)
        cell_load = congestion.get("cell_util", 0.5)
        for d in self.devices.values():
            sat_load = hot_load if (hot_sat is None or d.serving_satellite == hot_sat) else nominal_load
            spec = PROFILES[d.profile]
            if d.profile != "stationary":
                d.direction_deg = (d.direction_deg + self.rng.gauss(0, spec["turn_deg"])) % 360
                dist_m = d.velocity_ms * dt_s
                d.lat += (dist_m * math.cos(math.radians(d.direction_deg))) / METERS_PER_DEG_LAT
                d.lon += (dist_m * math.sin(math.radians(d.direction_deg))) / (
                    METERS_PER_DEG_LAT * max(0.3, math.cos(math.radians(d.lat))))
            # target radio values drift with load + noise (EMA alpha=0.25 => continuity)
            a = 0.25
            t_rsrp = -95 - 25 * cell_load + self.rng.gauss(0, 2)
            t_sinr = 12 - 14 * max(cell_load, sat_load) + self.rng.gauss(0, 1.2)
            t_lat = (28 + 45 * sat_load + 20 * cell_load
                     + 150 * max(0.0, sat_load - 0.75) + abs(self.rng.gauss(0, 4)))
            t_loss = max(0.0, 0.3 + 6.0 * max(0, sat_load - 0.7) + 2.0 * max(0, cell_load - 0.75) + self.rng.gauss(0, 0.2))
            t_tp = max(1.0, 60 * (1 - 0.7 * max(cell_load, sat_load)) + self.rng.gauss(0, 3))
            d.rsrp_dbm += a * (t_rsrp - d.rsrp_dbm)
            d.signal_strength_dbm = d.rsrp_dbm
            d.sinr_db += a * (t_sinr - d.sinr_db)
            d.rsrq_db += a * ((-19.5 + max(0.0, min(1.0, (d.sinr_db + 5) / 25.0)) * 14.0) - d.rsrq_db)
            d.latency_ms += a * (t_lat - d.latency_ms)
            d.packet_loss_pct += a * (t_loss - d.packet_loss_pct)
            d.throughput_mbps += a * (t_tp - d.throughput_mbps)
            d.jitter_ms += a * (max(1.0, d.latency_ms * 0.12 + self.rng.gauss(0, 1.5)) - d.jitter_ms)
            d.battery_pct = max(0.0, d.battery_pct - dt_s * 0.0005)
        return list(self.devices.values())

    def snapshot(self, limit: int = 500) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        out = []
        for d in list(self.devices.values())[:limit]:
            out.append({"device_id": d.device_id, "timestamp": now, "lat": round(d.lat, 5),
                        "lon": round(d.lon, 5), "velocity_ms": round(d.velocity_ms, 1),
                        "direction_deg": round(d.direction_deg, 1),
                        "serving_cell": d.serving_cell, "serving_satellite": d.serving_satellite,
                        "rsrp_dbm": round(d.rsrp_dbm, 1), "rsrq_db": round(d.rsrq_db, 1),
                        "signal_strength_dbm": round(d.signal_strength_dbm, 1),
                        "sinr_db": round(d.sinr_db, 1),
                        "candidate_cells": d.candidate_cells[:3],
                        "candidate_satellites": d.candidate_satellites[:3],
                        "latency_ms": round(d.latency_ms, 1), "packet_loss_pct": round(d.packet_loss_pct, 2),
                        "throughput_mbps": round(d.throughput_mbps, 1),
                        "jitter_ms": round(d.jitter_ms, 1), "battery_pct": round(d.battery_pct, 1),
                        "network_type": "NR" if d.sinr_db > 10 else "LTE",
                        "provenance": "SIMULATED"})
        return out
