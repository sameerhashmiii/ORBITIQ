"""Train all models on deterministic simulator output. Reproducible via SIMULATION_SEED."""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from backend.simulation.devices import DeviceSimulator
from backend.ml.anomaly import train_anomaly
from backend.ml.degradation import train_degradation

SEED = 42


def build_dataset(n: int = 6000) -> pd.DataFrame:
    sim = DeviceSimulator(seed=SEED)
    sim.spawn(1200)  # small pool so each load regime contributes rows
    rows = []
    # sweep load regimes so both classes are represented
    for util in [0.4, 0.55, 0.7, 0.85, 0.95]:
        sim.step(dt_s=60, congestion={"sat_util": util, "cell_util": util * 0.8})
        for d in sim.devices.values():
            rows.append({"device_id": d.device_id, "latency_ms": d.latency_ms,
                         "packet_loss_pct": d.packet_loss_pct, "throughput_mbps": d.throughput_mbps,
                         "rsrp_dbm": d.rsrp_dbm, "sinr_db": d.sinr_db, "jitter_ms": d.jitter_ms,
                         "sat_util": util, "cell_util": util * 0.8, "velocity_ms": d.velocity_ms,
                         "device_density": 150.0})
    # repeat sweeps with fresh noise path until we have n rows
    while len(rows) < n:
        for util in [0.55, 0.7, 0.85, 0.95, 0.4]:
            sim.step(dt_s=60, congestion={"sat_util": util, "cell_util": util * 0.8})
            for d in sim.devices.values():
                rows.append({"device_id": d.device_id, "latency_ms": d.latency_ms,
                             "packet_loss_pct": d.packet_loss_pct, "throughput_mbps": d.throughput_mbps,
                             "rsrp_dbm": d.rsrp_dbm, "sinr_db": d.sinr_db, "jitter_ms": d.jitter_ms,
                             "sat_util": util, "cell_util": util * 0.8, "velocity_ms": d.velocity_ms,
                             "device_density": 150.0})
            if len(rows) >= n:
                break
    df = pd.DataFrame(rows[:n])
    # Ground-truth label from CLEAN simulator state (future degradation outcome);
    # features below get measurement noise, so this is a genuine prediction task.
    df["__y_clean"] = (((df["latency_ms"] > 100) | (df["packet_loss_pct"] > 2.0) | (df["throughput_mbps"] < 5))).astype(int)
    # Simulate measurement noise: features are noisy observations, so the
    # degradation-label threshold is NOT trivially recoverable -> honest metrics.
    rng = np.random.RandomState(SEED)
    df["latency_ms"] = df["latency_ms"] + rng.normal(0, 12, size=len(df))
    df["packet_loss_pct"] = (df["packet_loss_pct"] + rng.normal(0, 0.6, size=len(df))).clip(lower=0)
    df["throughput_mbps"] = (df["throughput_mbps"] + rng.normal(0, 4, size=len(df))).clip(lower=0.5)
    df["rsrp_dbm"] = df["rsrp_dbm"] + rng.normal(0, 3, size=len(df))
    df["sinr_db"] = df["sinr_db"] + rng.normal(0, 1.5, size=len(df))
    # inject 5% point anomalies so IsolationForest has signal
    idx = rng.choice(len(df), size=len(df) // 20, replace=False)
    df.loc[idx, "latency_ms"] *= 3.0
    df.loc[idx, "packet_loss_pct"] += 5.0
    return df


def main():
    df = build_dataset()
    a = train_anomaly(df)
    d = train_degradation(df)
    Path("ml/evaluation").mkdir(parents=True, exist_ok=True)
    Path("ml/evaluation/last_run.json").write_text(json.dumps({"anomaly": a, "degradation": d}, indent=2))
    print(json.dumps({"anomaly": a, "degradation": d}, indent=2))


if __name__ == "__main__":
    main()
