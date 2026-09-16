"""Deterministic sample-data generator (public-format, synthetic-but-realistic).

Creates small committed snapshots so the demo works without API keys.
Cell layout mirrors OpenCelliD schema; TLEs are valid-format synthetic
LEO elements for demo propagation (clearly NOT SpaceX proprietary data).
"""
import csv
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"
SEED = 42

# Demo region: San Francisco Bay Area
CENTER_LAT, CENTER_LON = 37.7749, -122.4194


def make_cells(n: int = 1500) -> None:
    rng = random.Random(SEED)
    SAMPLE.mkdir(parents=True, exist_ok=True)
    radios = ["LTE"] * 60 + ["NR"] * 25 + ["UMTS"] * 10 + ["GSM"] * 5
    with open(SAMPLE / "opencellid_sample.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mcc", "mnc", "lac", "cellid", "radio", "lat", "lon", "range", "samples"])
        for i in range(n):
            # clustered around center with ~60km spread
            lat = rng.gauss(CENTER_LAT, 0.35)
            lon = rng.gauss(CENTER_LON, 0.40)
            w.writerow([310, rng.choice([260, 410, 120]), rng.randint(1000, 9999),
                        100000 + i, rng.choice(radios),
                        round(lat, 6), round(lon, 6),
                        rng.choice([500, 1000, 2000, 5000]), rng.randint(3, 200)])


def make_tles(n: int = 24) -> None:
    # Valid-format synthetic LEO TLEs (demo only). Checksum-safe enough for sgp4 demo;
    # sgp4 validates format, so we construct lines carefully via fixed template.
    # Inclination ~53deg, alt ~550km style mean motion ~15.06 rev/day.
    rng = random.Random(SEED)
    lines = []
    base_mm = 15.06
    for i in range(n):
        satnum = 90000 + i
        name = f"ORBITIQ-DEMO-{i:02d}"
        mm = base_mm + rng.uniform(-0.05, 0.05)
        ma = rng.uniform(0, 360)
        raan = rng.uniform(0, 360)
        # TLE lines (simplified but parseable by sgp4)
        l1 = f"1 {satnum:05d}U 24001A   24001.50000000  .00010000  00000-0  10000-3 0  100{i % 10}"
        l2 = f"2 {satnum:05d}  53.0542 {raan:8.4f} 0001200 {ma:8.4f}  90.0000 {mm:11.8f}    10"
        lines += [name, l1, l2]
    (SAMPLE / "celestrak_sample.tle").write_text("\n".join(lines) + "\n")


def make_space_weather() -> None:
    sw = {
        "source": "NOAA SWPC (sample snapshot)",
        "kp_index": 2.33,
        "a_index": 12,
        "solar_wind_kms": 412.5,
        "bz_gsm_nt": -1.8,
        "note": "REAL public-data format snapshot; contextual only, not a performance predictor.",
    }
    (SAMPLE / "noaa_sw_sample.json").write_text(json.dumps(sw, indent=2))


if __name__ == "__main__":
    make_cells()
    make_tles()
    make_space_weather()
    print("sample data written to", SAMPLE)
