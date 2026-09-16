"""Shared feature definitions for all ML models (versioned)."""
FEATURE_VERSION = "v1"
ANOMALY_FEATURES = ["latency_ms", "packet_loss_pct", "throughput_mbps", "rsrp_dbm", "sinr_db", "jitter_ms"]
DEGRADATION_FEATURES = ["latency_ms", "packet_loss_pct", "throughput_mbps", "rsrp_dbm", "sinr_db",
                        "jitter_ms", "velocity_ms"]
# NOTE: sat_util / cell_util / device_density are recorded in the dataset for
# analysis but EXCLUDED from model inputs — the model must predict degradation
# from noisy device-observable telemetry only (no load leak -> honest metrics).
HANDOFF_FEATURES = ["signal_dbm", "sinr_db", "elevation_deg", "slant_range_km", "latency_ms",
                    "capacity_score", "visibility_min", "congestion_pct", "degradation_prob"]

TARGET_DEGRADED = "degraded"  # latency>100ms OR loss>2% OR throughput<5Mbps
