# Limitations — ORBITIQ (read before citing this project)

- Independent prototype; **not a SpaceX/Starlink replica**, no proprietary data, no partnership implied.
- Orbital propagation uses public TLE + simplified WGS84 geometry (km-level, demo-grade).
- Radio propagation is simplified (no ray-tracing, fading, or 3GPP channel models); capacity partly simulated.
- All device telemetry is simulated (seeded); ML metrics describe the simulator domain, not real networks.
- Space weather is contextual display only.
- Demo TLE set is synthetic-but-valid-format; swap in real CelesTrak TLEs via `CELESTRAK_TLE` env.
- Not suitable for operational telecom deployment (no real OSS/BSS, SON, or regulatory interfaces).
