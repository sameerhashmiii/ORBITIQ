"""Shared Pydantic schemas with explicit data-provenance labels."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Provenance(str, Enum):
    REAL = "REAL"
    DERIVED = "DERIVED"
    SIMULATED = "SIMULATED"
    PREDICTION = "PREDICTION"
    RECOMMENDATION = "AI RECOMMENDATION"


class CellSite(BaseModel):
    cell_id: str
    mcc: int = 310
    mnc: int = 260
    tac: int = 0
    radio: str = "LTE"  # LTE | NR | UMTS | GSM
    lat: float
    lon: float
    range_m: int = 1000
    samples: int = 10
    provenance: Provenance = Provenance.REAL


class SatelliteState(BaseModel):
    sat_id: str
    name: str
    lat: float
    lon: float
    altitude_km: float
    elevation_deg: Optional[float] = None
    azimuth_deg: Optional[float] = None
    slant_range_km: Optional[float] = None
    visible: bool = False
    visibility_duration_min: Optional[float] = None
    utilization_pct: float = 50.0
    provenance_position: Provenance = Provenance.REAL
    provenance_geometry: Provenance = Provenance.DERIVED


class DeviceTelemetry(BaseModel):
    device_id: str
    timestamp: datetime
    lat: float
    lon: float
    velocity_ms: float = 0.0
    direction_deg: float = 0.0
    serving_cell: Optional[str] = None
    serving_satellite: Optional[str] = None
    rsrp_dbm: float = -100.0
    rsrq_db: float = -12.0
    sinr_db: float = 5.0
    latency_ms: float = 45.0
    packet_loss_pct: float = 0.5
    throughput_mbps: float = 25.0
    jitter_ms: float = 5.0
    battery_pct: float = 80.0
    network_type: str = "LTE"
    provenance: Provenance = Provenance.SIMULATED


class NetworkEvent(BaseModel):
    event_id: str
    timestamp: datetime
    type: str
    location_lat: float
    location_lon: float
    severity: str  # low | medium | high | critical
    root_cause: str = ""
    affected_devices: int = 0
    affected_cells: list[str] = Field(default_factory=list)
    affected_satellites: list[str] = Field(default_factory=list)


class DegradationPrediction(BaseModel):
    device_id: Optional[str] = None
    region_id: Optional[str] = None
    probability: float
    confidence: float
    predicted_minutes_to_degradation: Optional[float] = None
    horizon_min: int = 5
    provenance: Provenance = Provenance.PREDICTION


class HandoffCandidate(BaseModel):
    sat_id: str
    score: float
    signal_dbm: Optional[float] = None
    latency_ms: Optional[float] = None
    congestion_pct: Optional[float] = None
    visibility_min: Optional[float] = None


class HandoffRecommendation(BaseModel):
    device_id: str
    recommended_sat: str
    confidence: float
    ranked: list[HandoffCandidate]
    explanation: list[str]
    provenance: Provenance = Provenance.RECOMMENDATION
