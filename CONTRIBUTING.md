# Contributing to ORBITIQ

## Environment

- Backend: Python 3.9+ (`pip install -r backend/requirements.txt`), `PYTHONPATH` set to the repo root.
- Frontend: Node 20 (`cd frontend && npm ci`).
- Copy `.env.example` to `.env`. No API keys are required for the demo.

## Checks (run before opening a PR)

```bash
python ml/training/train_all.py                                    # reproduce ML artifacts + metrics
python -m pytest tests -q --cov=backend --cov-report=term-missing  # backend tests, target >80%
cd frontend && ./node_modules/.bin/tsc --noEmit                    # type check
python scripts/check_overflow.py                                   # layout regression, 0 px tolerance
python -m ruff check backend ml tests scripts                      # lint (policy: pyproject.toml)
python -m mypy backend --ignore-missing-imports                    # types
```

## Screenshots and video

UI captures must come from the real running application:

```bash
python scripts/capture_video_shots.py   # Playwright frames -> video/shots/
```

The 90-second film is assembled from those frames plus `docs/video/demo-narration.txt`
(see `docs/video/demo-storyboard.md`). Never commit mockups presented as product.

## Data and claims policy

- Real public data stays real: never replace OpenCelliD/CelesTrak/NOAA inputs with random values.
- Every new metric needs an origin (real / derived / simulated / predicted) and a UI provenance label.
- No accuracy claims without an evaluation artifact under `ml/evaluation/`.
- Device telemetry stays seeded and reproducible (`SIMULATION_SEED=42`).
- The independence disclaimer (README, app footer, docs) must survive every change.
