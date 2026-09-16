"""What-if engine: outage simulation BEFORE vs AFTER AI optimization (SIMULATION RESULT)."""
from __future__ import annotations

import copy

from backend.simulation.devices import DeviceSimulator


def run_outage_scenario(twin, sat_id: str) -> dict:
    """Simulate `sat_id` outage: affected users, alt satellites, KPI deltas before/after.

    BEFORE aggregates live twin telemetry. AFTER replays the affected device
    population through the simulator under the alternative satellite's load,
    so the improvement is simulated — never a hardcoded multiplier.
    """
    affected = [d for d in twin.sim.devices.values() if d.serving_satellite == sat_id]
    n = len(affected)
    affected_cells = sorted({d.serving_cell for d in affected if d.serving_cell})
    before_lat = sum(d.latency_ms for d in affected) / max(1, n)
    before_loss = sum(d.packet_loss_pct for d in affected) / max(1, n)
    before_tp = sum(d.throughput_mbps for d in affected) / max(1, n)
    before_degraded = sum(1 for d in affected if d.latency_ms > 100 or d.packet_loss_pct > 2.0)

    # AFTER: handoff to the least-loaded alternative satellite, then replay.
    alts = [t[0] for t in twin.tles if t[0] != sat_id]
    best_alt = min(alts, key=lambda s: twin.sat_util.get(s, 0.5)) if alts else None
    after_lat, after_loss, after_tp, after_degraded = before_lat, before_loss, before_tp, before_degraded
    if n and best_alt:
        scratch = DeviceSimulator(seed=twin.seed)
        scratch.devices = {d.device_id: copy.deepcopy(d) for d in affected}
        for d in scratch.devices.values():
            d.serving_satellite = best_alt
        scratch.step(dt_s=60, congestion={"sat_util": twin.sat_util.get(best_alt, 0.5),
                                           "cell_util": 0.5})
        for _ in range(5):  # let EMA telemetry converge toward the healthy target
            scratch.step(dt_s=60, congestion={"sat_util": twin.sat_util.get(best_alt, 0.5),
                                              "cell_util": 0.5})
        moved = list(scratch.devices.values())
        after_lat = sum(d.latency_ms for d in moved) / len(moved)
        after_loss = sum(d.packet_loss_pct for d in moved) / len(moved)
        after_tp = sum(d.throughput_mbps for d in moved) / len(moved)
        after_degraded = sum(1 for d in moved if d.latency_ms > 100 or d.packet_loss_pct > 2.0)

    return {
        "scenario": f"{sat_id} outage",
        "affected_devices": n,
        "affected_cells": affected_cells[:10],
        "affected_cells_count": len(affected_cells),
        "alternative_satellites": alts[:3],
        "recommended": best_alt,
        "before": {"avg_latency_ms": round(before_lat, 1), "avg_loss_pct": round(before_loss, 2),
                   "avg_throughput_mbps": round(before_tp, 1), "degraded_users": before_degraded},
        "after_ai_optimization": {"avg_latency_ms": round(after_lat, 1), "avg_loss_pct": round(after_loss, 2),
                                  "avg_throughput_mbps": round(after_tp, 1), "degraded_users": after_degraded},
        "handoff_volume": n,
        "provenance": "SIMULATION RESULT",
    }
