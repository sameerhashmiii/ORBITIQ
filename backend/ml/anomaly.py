"""Anomaly detection: IsolationForest over telemetry (Model 1)."""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.ml.features import ANOMALY_FEATURES

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "models" / "demo" / "anomaly_iforest.pkl"


def train_anomaly(df: pd.DataFrame) -> dict:
    X = df[ANOMALY_FEATURES].fillna(df[ANOMALY_FEATURES].median(numeric_only=True))
    clf = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
    clf.fit(X)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "features": ANOMALY_FEATURES, "version": "v1"}, MODEL_PATH)
    scores = -clf.score_samples(X)
    return {"n": len(X), "mean_score": float(scores.mean()), "p95": float(np.percentile(scores, 95))}


def score_anomaly(rows: list[dict]) -> list[dict]:
    bundle = joblib.load(MODEL_PATH)
    clf, feats = bundle["model"], bundle["features"]
    X = pd.DataFrame(rows)[feats].fillna(0)
    scores = -clf.score_samples(X)
    preds = clf.predict(X)  # 1 normal, -1 anomaly
    critical_at = float(np.percentile(scores, 90)) if len(scores) else float("inf")
    out = []
    for i, r in enumerate(rows):
        sev = "normal" if preds[i] == 1 else ("critical" if scores[i] > critical_at else "high")
        lat, lon = r.get("lat"), r.get("lon")
        area = f"grid:{round(lat, 1)},{round(lon, 1)}" if lat is not None and lon is not None else "unknown"
        out.append({"device_id": r.get("device_id"), "anomaly_score": round(float(scores[i]), 3),
                    "severity": sev, "affected_area": area, "provenance": "PREDICTION"})
    return out
