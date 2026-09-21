"""Network event engine — deterministic scenario injector."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

EVENT_TYPES = ["CELL_CONGESTION", "SATELLITE_CONGESTION", "SATELLITE_VISIBILITY_LOSS",
               "HANDOFF_APPROACHING", "SIGNAL_DEGRADATION", "LATENCY_SPIKE", "PACKET_LOSS_SPIKE",
               "GROUND_STATION_OUTAGE", "CELL_SITE_OUTAGE", "SPACE_WEATHER_EVENT",
               "BACKHAUL_DEGRADATION", "DEVICE_DENSITY_SPIKE"]

RECOMMENDED_ACTIONS = {
    "CELL_CONGESTION": "Offload edge devices to neighboring cells; evaluate satellite backhaul.",
    "SATELLITE_CONGESTION": "Rank alternative visible satellites and execute handoff for degraded devices.",
    "SATELLITE_VISIBILITY_LOSS": "Pre-compute handoff targets before the visibility window closes.",
    "HANDOFF_APPROACHING": "Prepare ranked handoff candidates; notify affected devices.",
    "SIGNAL_DEGRADATION": "Check interference and cell load; consider band/satellite reassignment.",
    "LATENCY_SPIKE": "Inspect backhaul and satellite path; reroute through lower-latency link.",
    "PACKET_LOSS_SPIKE": "Inspect congested link; shift traffic to alternative path.",
    "GROUND_STATION_OUTAGE": "Reroute satellite traffic through backup ground station.",
    "CELL_SITE_OUTAGE": "Fail over to neighboring cells + satellite direct-to-cell coverage.",
    "SPACE_WEATHER_EVENT": "Monitor link margins; no automated action (contextual data only).",
    "BACKHAUL_DEGRADATION": "Shift load to alternative backhaul/satellite path.",
    "DEVICE_DENSITY_SPIKE": "Add temporary capacity; load-balance across cells.",
}


def make_event(event_type: str, lat: float, lon: float, severity: str = "high",
               affected_devices: int = 0, affected_cells: list | None = None,
               affected_satellites: list | None = None,
               root_cause: str = "", telemetry_changes: dict | None = None) -> dict:
    assert event_type in EVENT_TYPES, f"unknown event {event_type}"
    return {
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "location": {"lat": lat, "lon": lon},
        "severity": severity,
        "root_cause": root_cause,
        "recommended_action": RECOMMENDED_ACTIONS.get(event_type, "Investigate via copilot."),
        "affected_devices": affected_devices,
        "affected_cells": affected_cells or [],
        "affected_satellites": affected_satellites or [],
        "telemetry_changes": telemetry_changes or {},
    }


def demo_congestion_scenario(center=(37.7749, -122.4194), sats=None) -> list[dict]:
    """Predefined deterministic incident: SAT congestion -> degradation (recruiter demo).

    `sats` carries the live satellite IDs ([primary, secondary]); defaults keep
    the offline snapshot story readable.
    """
    lat, lon = center
    primary = sats[0] if sats else "ORBITIQ-DEMO-07"
    secondary = sats[1] if sats and len(sats) > 1 else "ORBITIQ-DEMO-11"
    return [
        make_event("SATELLITE_CONGESTION", lat, lon, "high", 0, [],
                   [primary], "offered load exceeded beam capacity",
                   {"sat_util": [0.55, 0.94], "latency_ms": [61, 111], "packet_loss_pct": [0.4, 1.7]}),
        make_event("SIGNAL_DEGRADATION", lat + 0.05, lon - 0.03, "medium", 0, [],
                   [primary], "SINR drop from congestion",
                   {"sinr_db": [9.5, 2.1]}),
        make_event("HANDOFF_APPROACHING", lat, lon, "medium", 0, [],
                   [primary, secondary], "visibility window closing in ~4 min", {}),
    ]
