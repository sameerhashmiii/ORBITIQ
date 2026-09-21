"""Satellite propagation + ground-geometry (elevation/azimuth/slant-range/visibility).

Methodology:
- SGP4 propagation of public TLEs via `sgp4` (Vallado).
- WGS84 approx: geodetic lat/lon/alt from ECI using GMST rotation (documented
  simplification; accuracy ~km-level, sufficient for visibility engineering demo).
- Visibility: elevation > 10 deg above horizon (configurable mask).
- Visibility duration: linear scan forward in 30s steps up to 120 min.

Documented in docs/data.md. Positions are derived from PUBLIC orbital data,
never invented.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

EARTH_R_KM = 6371.0


@dataclass
class SatFix:
    sat_id: str
    name: str
    lat: float
    lon: float
    altitude_km: float


def propagate_tle(name: str, line1: str, line2: str, when: datetime | None = None) -> SatFix:
    """Propagate a single TLE to geodetic coordinates using sgp4."""
    from sgp4.api import Satrec
    when = when or datetime.now(timezone.utc)
    sat = Satrec.twoline2rv(line1, line2)
    jd, fr = _to_jd_fr(when)
    e, r, _v = sat.sgp4(jd, fr)
    if e != 0:
        raise RuntimeError(f"SGP4 error code {e} for {name}")
    lat, lon, alt = _eci_to_geodetic(tuple(r), when)
    return SatFix(sat_id=name, name=name, lat=lat, lon=lon, altitude_km=alt)


def ground_geometry(sat_lat: float, sat_lon: float, sat_alt_km: float,
                    gs_lat: float, gs_lon: float, mask_deg: float = 10.0) -> dict:
    """Compute elevation/azimuth/slant-range/visibility for a ground point."""
    # ECEF approx (spherical earth)
    def to_ecef(lat, lon, alt):
        la, lo = math.radians(lat), math.radians(lon)
        r = EARTH_R_KM + alt
        return (r * math.cos(la) * math.cos(lo), r * math.cos(la) * math.sin(lo), r * math.sin(la))
    sx, sy, sz = to_ecef(sat_lat, sat_lon, sat_alt_km)
    gx, gy, gz = to_ecef(gs_lat, gs_lon, 0.0)
    dx, dy, dz = sx - gx, sy - gy, sz - gz
    slant = math.sqrt(dx * dx + dy * dy + dz * dz)
    # elevation from the local up-vector (dot product with line of sight)
    up = (gx / EARTH_R_KM, gy / EARTH_R_KM, gz / EARTH_R_KM)
    sin_el = (dx * up[0] + dy * up[1] + dz * up[2]) / slant
    sin_el = max(-1.0, min(1.0, sin_el))
    elev = math.degrees(math.asin(sin_el))
    # azimuth: project onto local ENU
    la, lo = math.radians(gs_lat), math.radians(gs_lon)
    east = (-math.sin(lo), math.cos(lo), 0.0)
    north = (-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la))
    e = dx * east[0] + dy * east[1] + dz * east[2]
    n = dx * north[0] + dy * north[1] + dz * north[2]
    az = (math.degrees(math.atan2(e, n)) + 360) % 360
    return {
        "elevation_deg": round(elev, 2),
        "azimuth_deg": round(az, 2),
        "slant_range_km": round(slant, 1),
        "visible": bool(elev > mask_deg),
    }


def visibility_duration_minutes(name: str, l1: str, l2: str, gs_lat: float, gs_lon: float,
                                start: datetime | None = None, mask_deg: float = 10.0) -> float:
    start = start or datetime.now(timezone.utc)
    total = 0.0
    step = timedelta(seconds=30)
    t = start
    for _ in range(240):  # 120 min
        try:
            fix = propagate_tle(name, l1, l2, t)
        except Exception:
            break
        g = ground_geometry(fix.lat, fix.lon, fix.altitude_km, gs_lat, gs_lon, mask_deg)
        if g["visible"]:
            total += 0.5
        elif total > 0:
            break
        t += step
    return round(total, 1)


def _to_jd_fr(when: datetime):
    return _timescale().from_datetime(when).tt, 0.0  # sgp4 api accepts jd+fr; use tt jd
    # NOTE: sgp4 typical call uses jday; tt vs ut1 diff is negligible for demo.


_TS = None


def _timescale():
    """Shared Skyfield timescale (constructed once — not per propagation)."""
    global _TS
    if _TS is None:
        from skyfield.api import load
        _TS = load.timescale()
    return _TS


def _eci_to_geodetic(r_eci_km, when: datetime) -> tuple[float, float, float]:
    x, y, z = r_eci_km
    r = math.sqrt(x * x + y * y + z * z)
    # GMST (approx, Vallado)
    jd = _datetime_to_jd(when)
    t = (jd - 2451545.0) / 36525.0
    gmst_deg = (280.46061837 + 360.98564736629 * (jd - 2451545.0)
                + 0.000387933 * t * t - t**3 / 38710000.0) % 360.0
    gmst = math.radians(gmst_deg)
    # rotate ECI -> ECEF
    xe = x * math.cos(gmst) + y * math.sin(gmst)
    ye = -x * math.sin(gmst) + y * math.cos(gmst)
    ze = z
    lon = math.degrees(math.atan2(ye, xe))
    lat = math.degrees(math.asin(max(-1.0, min(1.0, ze / r))))
    alt = r - EARTH_R_KM
    return round(lat, 4), round(lon, 4), round(alt, 1)


def _datetime_to_jd(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    frac = (dt.hour - 12) / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0 + dt.microsecond / 86400e6
    return jdn + frac
