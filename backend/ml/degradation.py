"""Connectivity-degradation prediction: interpretable RandomForest (Model 2).

Why RandomForest over deep learning: tabular telemetry, small demo data,
interpretability (feature importances), fast CPU inference. Documented in
docs/engineering-decisions.md.
"""
from __future__ import annotations
from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from backend.ml.features import DEGRADATION_FEATURES, TARGET_DEGRADED

MODEL_PATH = Path("ml/models/demo/degradation_rf.pkl")


def label_degraded(df: pd.DataFrame) -> pd.Series:
    if "__y_clean" in df.columns:  # genuine prediction: noisy features, clean outcome label
        return df["__y_clean"].astype(int)
    return ((df["latency_ms"] > 100) | (df["packet_loss_pct"] > 2.0) | (df["throughput_mbps"] < 5)).astype(int)


def train_degradation(df: pd.DataFrame) -> dict:
    X = df[DEGRADATION_FEATURES].fillna(0)
    y = label_degraded(df)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    clf = RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_leaf=5,
                                 class_weight="balanced", random_state=42, n_jobs=-1)
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)[:, 1]
    pred = (proba >= 0.5).astype(int)
    metrics = {
        "precision": round(float(precision_score(yte, pred, zero_division=0)), 3),
        "recall": round(float(recall_score(yte, pred, zero_division=0)), 3),
        "f1": round(float(f1_score(yte, pred, zero_division=0)), 3),
        "roc_auc": round(float(roc_auc_score(yte, proba)), 3),
        "n_train": len(Xtr), "n_test": len(Xte),
        "positive_rate": round(float(y.mean()), 3),
        "importances": dict(sorted(zip(DEGRADATION_FEATURES, clf.feature_importances_.round(3).tolist()),
                                   key=lambda kv: kv[1], reverse=True)),
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "features": DEGRADATION_FEATURES, "metrics": metrics, "version": "v1"}, MODEL_PATH)
    (MODEL_PATH.parent / "degradation_metrics.json").write_text(__import__("json").dumps(metrics, indent=2))
    return metrics


def predict_degradation(rows: list[dict], horizon_min: int = 5) -> list[dict]:
    bundle = joblib.load(MODEL_PATH)
    clf, feats = bundle["model"], bundle["features"]
    X = pd.DataFrame(rows)[feats].fillna(0) if rows else pd.DataFrame(columns=feats)
    out = []
    if len(X):
        proba = clf.predict_proba(X)[:, 1]
        for i, r in enumerate(rows):
            p = float(proba[i])
            out.append({"device_id": r.get("device_id"), "probability": round(p, 3),
                        "confidence": round(float(max(p, 1 - p)), 3),
                        "predicted_minutes_to_degradation": round(horizon_min * p, 1) if p > 0.5 else None,
                        "horizon_min": horizon_min, "provenance": "PREDICTION"})
    return out
