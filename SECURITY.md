# Security Policy — ORBITIQ

## Secrets
- All credentials via environment variables; see `.env.example`. No secrets in Git.
- `OPENCELLID_API_KEY`, `LLM_API_KEY`, `API_KEY` are optional; the demo works without them.

## API security
- CORS allowlist via `CORS_ORIGINS`. Security headers via reverse proxy in production.
- Input validation with Pydantic on all POST bodies; query bounds via FastAPI `Query(le=…)`.
- Optional `API_KEY` bearer check can be enabled at the gateway.

## Data handling
- Only public datasets (OpenCelliD CC BY-SA 4.0 with attribution, CelesTrak public TLE, NOAA public domain).
- No user PII: device IDs are synthetic simulator identifiers.

## Dependencies
- Pinned requirements; CI runs Bandit + `pip audit`-style review; frontend `npm audit` in CI.
- Rate limiting recommended at ingress (nginx/Cloudflare) for `/copilot` and `/simulation` POST routes.

## Logging
- Structured logging; no telemetry payloads with identifiers in logs.
