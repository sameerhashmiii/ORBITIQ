# Demo script / storyboard / narration — ORBITIQ 90-second video
See `video/orbitIQ-demo.vtt` for captions. Shots follow the 10-shot plan in the
spec (intro → real cellular → satellites → twin → incident → prediction →
handoff → what-if → copilot → final).

## Automated generation (used for the committed video — actual app only)
1. Start backend (`uvicorn backend.main:app`) + frontend (`npm run dev`).
2. `python3 scripts/capture_video_shots.py` — Playwright/Chromium screenshots the
   REAL running app while driving the demo flow (inject → predict → rank →
   what-if → copilot). Frames land in `video/shots/`.
3. `say -r <rate> -f docs/video/demo-narration.txt -o video/narration.aiff`
   (macOS TTS; rate tuned so narration ≈ 82 s).
4. Assemble (ffmpeg static build via `imageio-ffmpeg`):
   slideshow (5/8/8/8/10/8/10/8/10/7 s = 82 s, 30 fps, 1280×720) + narration
   padded to 82 s → `video/orbitIQ-demo.mp4` (H.264/AAC) +
   `video/orbitIQ-demo.webm` (VP9/Opus); thumbnail = real frame at t=3 s.
5. Web copies in `frontend/public/video/` so the in-app player serves them.

## Deterministic manual alternative (no Playwright/ffmpeg-python)
1. `docker compose up --build` (or backend `uvicorn backend.main:app` + `cd frontend && npm run dev`)
2. Open `http://localhost:5173/#/recruiter`, press **Start Recruiter Tour** (drives the 12-step story deterministically).
3. Record with FFmpeg:
   `ffmpeg -f avfoundation -i 1 -r 30 raw.mp4` (macOS) or `ffmpeg -f x11grab -i :0.0 raw.mp4` (Linux)
4. Narration: `docs/video/demo-narration.txt` (macOS `say`, or any TTS) → `narration.wav`
5. Assemble: `ffmpeg -i raw.mp4 -i narration.wav -c:v libx264 -c:a aac -shortest video/orbitIQ-demo.mp4`
   + `ffmpeg -i video/orbitIQ-demo.mp4 -c:v libvpx-vp9 video/orbitIQ-demo.webm`
6. Thumbnail: `video/thumbnail.png` (committed placeholder; replace with a real frame: `ffmpeg -ss 3 -i video/orbitIQ-demo.mp4 -frames:v 1 video/thumbnail.png`).

No fake screenshots: every frame must come from this workflow. Until recorded, the app shows
"Demo video unavailable — Launch Interactive Demo" via the HTML5 `<video>` fallback.
