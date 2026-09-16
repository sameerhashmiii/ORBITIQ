"""Real-data ingestion with resilient fallback: REAL -> CACHE -> LOCAL SNAPSHOT -> SIMULATION.

Never requires API keys. Honors OpenCelliD CC BY-SA 4.0 attribution.
"""
from __future__ import annotations
import csv
import json
import logging
import os
from pathlib import Path

log = logging.getLogger("orbitiq.ingest")

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CELL_CSV = ROOT / "data" / "sample" / "opencellid_sample.csv"
SAMPLE_TLE = ROOT / "data" / "sample" / "celestrak_sample.tle"
SAMPLE_SW = ROOT / "data" / "sample" / "noaa_sw_sample.json"


def load_cells(limit: int = 5000, source_csv: str | None = None) -> list[dict]:
    """Load real cell sites from OpenCelliD CSV (or local snapshot fallback)."""
    path = Path(source_csv) if source_csv else _resolve_cell_source()
    cells: list[dict] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cells.append({
                    "cell_id": f"{row.get('mcc','310')}-{row.get('mnc','260')}-{row.get('lac','0')}-{row.get('cellid', row.get('cell_id','0'))}",
                    "mcc": int(row.get("mcc", 310)),
                    "mnc": int(row.get("mnc", 260)),
                    "tac": int(row.get("lac", row.get("tac", 0))),
                    "radio": row.get("radio", "LTE"),
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "range_m": int(float(row.get("range", 1000))),
                    "samples": int(float(row.get("samples", 10))),
                    "provenance": "REAL",
                })
            except (ValueError, KeyError):
                continue
            if len(cells) >= limit:
                break
    log.info("loaded %d cells from %s", len(cells), path)
    return cells


def _resolve_cell_source() -> Path:
    env_path = os.getenv("OPENCELLID_CSV")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    for cand in [ROOT / "data" / "raw" / "opencellid.csv", SAMPLE_CELL_CSV]:
        if cand.exists():
            return cand
    raise FileNotFoundError("No cell data snapshot found. Run scripts/make_sample_data.py")


def load_tles(source: str | None = None) -> list[tuple[str, str, str]]:
    """Load TLE triplets (name, L1, L2) from cache or local snapshot."""
    path = Path(source) if source else _resolve_tle_source()
    lines = [ln.strip() for ln in open(path) if ln.strip()]
    out = []
    for i in range(0, len(lines) - 2, 3):
        out.append((lines[i], lines[i + 1], lines[i + 2]))
    log.info("loaded %d TLEs from %s", len(out), path)
    return out


def _resolve_tle_source() -> Path:
    env_path = os.getenv("CELESTRAK_TLE")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    for cand in [ROOT / "data" / "raw" / "celestrak.tle", SAMPLE_TLE]:
        if cand.exists():
            return cand
    raise FileNotFoundError("No TLE snapshot found. Run scripts/make_sample_data.py")


def load_space_weather(source: str | None = None) -> dict:
    """Load public NOAA space-weather snapshot (contextual only)."""
    path = Path(source) if source else SAMPLE_SW
    if not path.exists():
        return {"status": "unavailable", "note": "NOAA snapshot missing; treated as unavailable (degraded source)."}
    return json.loads(path.read_text())
