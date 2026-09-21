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
LIVE_CELL_CACHE = ROOT / "data" / "raw" / "opencellid_live.json"
LIVE_TLE_CACHE = ROOT / "data" / "raw" / "celestrak.tle"
COOLDOWN_FILE = ROOT / "data" / "raw" / ".opencellid_cooldown"

OPENCELLID_AREA_URL = "https://opencellid.org/cell/getInArea"
# Demo corridor: San Francisco core. Tiles stay under OpenCelliD's
# 4,000,000 sqm per-request cap. BBOX order is latmin,lonmin,latmax,lonmax.
DEMO_BBOX = (37.70, -122.52, 37.81, -122.36)
TILE_DEG = 0.018
MAX_LIVE_CELLS = 2000
MAX_LIVE_REQUESTS = 120


def _cooling_down() -> bool:
    """True while a recorded daily-limit cooldown is in effect (UTC midnight)."""
    try:
        if COOLDOWN_FILE.exists():
            import time
            retry_after = float(COOLDOWN_FILE.read_text().strip())
            if time.time() < retry_after:
                return True
            COOLDOWN_FILE.unlink()
    except Exception as e:
        log.debug("cooldown check failed: %s", e)
    return False


def _record_cooldown() -> None:
    """Stop live attempts until next UTC midnight (quota resets daily)."""
    try:
        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc)
        midnight = (now + _dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
        COOLDOWN_FILE.write_text(str(midnight.timestamp()))
        log.warning("OpenCelliD daily limit hit; cooling down until UTC midnight")
    except Exception as e:
        log.debug("cooldown record failed: %s", e)


def _is_quota_error(data: dict) -> bool:
    return isinstance(data, dict) and data.get("code") in (7, 8, 9)  # daily/rate limit family


def _snapshot_mode() -> bool:
    """Deterministic offline mode: snapshots only, no network (used by CI)."""
    return os.getenv("ORBITIQ_DATA", "").lower() == "snapshot"
    """Deterministic offline mode: snapshots only, no network (used by CI)."""
    return os.getenv("ORBITIQ_DATA", "").lower() == "snapshot"


def _num(v, default, cast):
    """Lenient numeric parse: real-world dumps have empty/garbage fields."""
    try:
        if v is None or v == "":
            return default
        return cast(v)
    except (ValueError, TypeError):
        return default


def _normalize_row(row: dict) -> dict | None:
    """Map one cell record (snapshot OR official dump OR live API schema) to canonical form."""
    mcc = _num(row.get("mcc", 310), 310, int)
    mnc = _num(row.get("mnc", row.get("net", 260)), 260, int)
    tac = _num(row.get("lac", row.get("tac", row.get("area", 0))), 0, int)
    cid = _num(row.get("cellid", row.get("cell_id", row.get("cell", 0))), 0, int)
    lat = _num(row.get("lat"), None, float)
    lon = _num(row.get("lon"), None, float)
    if lat is None or lon is None:
        return None
    return {
        "cell_id": f"{mcc}-{mnc}-{tac}-{cid}",
        "mcc": mcc,
        "mnc": mnc,
        "tac": tac,
        "radio": (row.get("radio", "LTE") or "LTE").upper(),
        "lat": lat,
        "lon": lon,
        "range_m": _num(row.get("range", 1000), 1000, lambda v: int(float(v))),
        "samples": _num(row.get("samples", 10), 10, lambda v: int(float(v))),
        "provenance": "REAL",
    }


def load_cells(limit: int = 5000, source_csv: str | None = None) -> list[dict]:
    """Load real cell sites.

    Priority: explicit CSV > live OpenCelliD fetch (key present) >
    live cache > local snapshot. Snapshot mode (`ORBITIQ_DATA=snapshot`)
    skips the network entirely for deterministic runs.
    """
    if source_csv:
        return _load_csv(Path(source_csv), limit)
    if not _snapshot_mode() and os.getenv("OPENCELLID_API_KEY"):
        if _cooling_down():
            log.info("OpenCelliD cooling down; using snapshot/cache")
        else:
            try:
                cells = _load_live_cells(limit)
                if cells:
                    return cells
            except Exception as e:
                log.warning("live OpenCelliD fetch failed, falling back: %s", e)
    if not _snapshot_mode():
        cached = _load_live_cache(limit)
        if cached:
            return cached
    return _load_csv(_resolve_cell_source(), limit)


def _load_csv(path: Path, limit: int) -> list[dict]:
    """Load real cell sites from an OpenCelliD CSV snapshot or full dump."""
    cells: list[dict] = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                norm = _normalize_row(row)
            except (ValueError, KeyError, TypeError):
                continue
            if norm is None:
                continue
            cells.append(norm)
            if len(cells) >= limit:
                break
    log.info("loaded %d cells from %s", len(cells), path)
    return cells


def _load_live_cache(limit: int) -> list[dict]:
    if not LIVE_CELL_CACHE.exists():
        return []
    try:
        data = json.loads(LIVE_CELL_CACHE.read_text())
        cells = data.get("cells", [])
        log.info("loaded %d cells from live cache %s", min(len(cells), limit), LIVE_CELL_CACHE)
        return cells[:limit]
    except Exception as e:
        log.warning("live cache unreadable: %s", e)
        return []


def _load_live_cells(limit: int) -> list[dict]:
    """Fetch real towers from OpenCelliD, tiled under the per-request area cap.

    Tiles the WHOLE corridor first, then spatially-uniform subsamples to the
    target — otherwise the first tiles fill the quota and towers bunch up in
    one corner of the map.
    """
    import httpx
    if os.getenv("OPENCELLID_REFRESH") != "1" and LIVE_CELL_CACHE.exists():
        return _load_live_cache(limit)  # credits cost nothing twice
    key = os.getenv("OPENCELLID_API_KEY", "")
    latmin, lonmin, latmax, lonmax = DEMO_BBOX
    pool: list[dict] = []
    seen: set[str] = set()
    reqs = 0
    lat = latmin
    while lat < latmax and reqs < MAX_LIVE_REQUESTS:
        lon = lonmin
        while lon < lonmax and reqs < MAX_LIVE_REQUESTS:
            tile = (lat, lon, min(lat + TILE_DEG, latmax), min(lon + TILE_DEG, lonmax))
            offset = 0
            while True:
                reqs += 1
                r = httpx.get(OPENCELLID_AREA_URL, params={
                    "key": key,
                    "BBOX": f"{tile[0]},{tile[1]},{tile[2]},{tile[3]}",
                    "format": "json", "limit": 50, "offset": offset}, timeout=30)
                r.raise_for_status()
                data = r.json()
                if "error" in data:
                    if _is_quota_error(data):
                        _record_cooldown()
                    raise RuntimeError(f"OpenCelliD: {data}")
                batch = data.get("cells", [])
                for row in batch:
                    try:
                        norm = _normalize_row(row)
                    except (ValueError, KeyError, TypeError):
                        continue
                    if norm and norm["cell_id"] not in seen:
                        seen.add(norm["cell_id"])
                        pool.append(norm)
                if len(batch) < 50 or reqs >= MAX_LIVE_REQUESTS:
                    break
                offset += 50
            lon += TILE_DEG
        lat += TILE_DEG
    if not pool:
        raise RuntimeError("live fetch returned no cells")
    # Even geographic coverage: stable sort, then uniform stride to target.
    pool.sort(key=lambda c: c["cell_id"])
    target = min(limit, MAX_LIVE_CELLS)
    stride = max(1, len(pool) // target)
    cells = pool[::stride][:target]
    LIVE_CELL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    LIVE_CELL_CACHE.write_text(json.dumps(
        {"cells": cells, "bbox": DEMO_BBOX, "pool": len(pool)}, indent=1))
    log.info("fetched %d live cells (pool %d) in %d requests (cached)", len(cells), len(pool), reqs)
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
    """Load TLE triplets (name, L1, L2): explicit file > live CelesTrak >
    live cache > local snapshot. Snapshot mode skips the network."""
    if source:
        return _parse_tles(Path(source).read_text().splitlines(), str(source))
    if not _snapshot_mode():
        try:
            return _load_live_tles()
        except Exception as e:
            log.warning("live CelesTrak fetch failed, falling back: %s", e)
        cached = _parse_tle_file(LIVE_TLE_CACHE)
        if cached:
            return cached
    return _parse_tle_file(_resolve_tle_source())


def _parse_tles(lines: list[str], origin: str) -> list[tuple[str, str, str]]:
    clean = [ln.strip() for ln in lines if ln.strip()]
    out = []
    for i in range(0, len(clean) - 2, 3):
        name, l1, l2 = clean[i], clean[i + 1], clean[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            out.append((name, l1, l2))
    log.info("loaded %d TLEs from %s", len(out), origin)
    return out


def _parse_tle_file(path: Path) -> list[tuple[str, str, str]]:
    if not path.exists():
        return []
    try:
        return _parse_tles(path.read_text().splitlines(), str(path))
    except Exception as e:
        log.warning("TLE file unreadable %s: %s", path, e)
        return []


def _load_live_tles() -> list[tuple[str, str, str]]:
    """Fetch the current public TLE group from CelesTrak (no key needed)."""
    import httpx
    if os.getenv("CELESTRAK_REFRESH") != "1" and LIVE_TLE_CACHE.exists():
        cached = _parse_tle_file(LIVE_TLE_CACHE)
        if cached:
            return cached
    url = os.getenv("CELESTRAK_URL", "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle")
    r = httpx.get(url, timeout=60, follow_redirects=True)
    r.raise_for_status()
    out = _parse_tles(r.text.splitlines(), f"live:{url}")
    if len(out) < 5:
        raise RuntimeError(f"live TLE fetch returned only {len(out)} objects")
    LIVE_TLE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    LIVE_TLE_CACHE.write_text(r.text)
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
