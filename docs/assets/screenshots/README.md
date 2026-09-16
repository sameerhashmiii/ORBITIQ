# Screenshot capture manifest

All images in this directory are captures of the **real running ORBITIQ application**
(React frontend at `:5173` backed by the FastAPI twin at `:8000`), taken against the
deterministic demo (`SIMULATION_SEED=42`). No mockups, no edited values.

| File | State shown |
|---|---|
| `home.png` | Command-center home: live stat cards, provenance chips, demo CTAs |
| `map.png` | Global map: OpenCelliD-format cells, SGP4 satellites, density grid, incidents |
| `incidents.png` | Incident timeline after congestion injection, with AI diagnosis + recommended action |
| `prediction.png` | Degradation predictions and anomaly counts over sampled devices |
| `handoff.png` | Ranked handoff candidates, recommendation, per-factor explanation |
| `whatif.png` | Outage what-if BEFORE vs AFTER AI optimization |
| `copilot.png` | Grounded copilot answer with confidence and sources |

## Reproduce

```bash
uvicorn backend.main:app --port 8000        # or docker compose up --build
cd frontend && npm run dev
python scripts/capture_video_shots.py       # writes video/shots/*.png
```

Copy the frames here to refresh this set. The 90-second film (`video/orbitIQ-demo.mp4`)
is assembled from the same frames; see `docs/video/demo-storyboard.md`.
