# Fulcrum

**AI incident response agent** — runs parallel remediation attempts on isolated containers, adapts its strategy based on error signatures, and hands off a compressed diagnosis (not a log dump) when human action is required.

[![Import to Superplane](https://img.shields.io/badge/Import%20to-Superplane-6366f1?style=for-the-badge)](https://app.superplane.com/canvas/import?url=https://raw.githubusercontent.com/eddie-nv/fulcrum/main/canvas.yaml)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/eddie-nv/fulcrum)

---

## How it works

```
Incident webhook
      │
POST /investigate ──── creates session, Baton room
      │
GET /snapshot ───────── captures broken container state
      │
┌─────┴──────┬──────────────┐          LEVEL 1
│            │              │
rollback   restart   fix-redis-port
 ✗           ✗              ✗ partial
      │
POST /plan ──────────── Claude picks next strategies
      │
┌─────┴──────┬──────────────┐          LEVEL 2
│            │              │
add-backoff  add-circuit-   fix-redis+backoff
             breaker
 ✗           ✗              ✓ PASSES
      │
POST /apply ─────────── winning strategy to production
      │
GET /card ───────────── compressed FeatureCard (≤500 tokens)
      │
Slack notification
```

**Token efficiency:**

| Approach | Tokens per fork |
|---|---|
| Full conversation replay | 15,000–50,000 |
| Fulcrum FeatureCard | ~500 |
| Savings | **30–100×** |

---

## Quick start

```bash
# Start all services (target:v1, target:v2, redis, payment-provider)
docker compose up

# Verify the break
curl localhost:3001/health   # → 200 ok
curl localhost:3002/health   # → 503 unhealthy

# Run the Fulcrum API locally
pip install -r requirements.txt
cp .env.example .env         # add ANTHROPIC_API_KEY
uvicorn fulcrum.main:app --port 8000

# Trigger an investigation
curl -X POST localhost:8000/investigate \
  -H "Content-Type: application/json" \
  -d '{"container_id": "fulcrum-target-v2-1", "error_signature": "redis: ECONNREFUSED"}'
```

---

## Architecture

| Component | Description |
|---|---|
| `fulcrum/` | FastAPI incident response API |
| `target/` | Express.js demo service (Node.js 22) |
| `payment-provider/` | Mock payment API — deterministic 50% 429 rate |
| `redis` | Cache on port 6380 |
| `baton` | Event-sourcing state fabric (optional, `--profile baton`) |

**Stack:** FastAPI · Docker Python SDK · Anthropic Claude API · Superplane · Baton · Render

---

## API

| Endpoint | Description |
|---|---|
| `POST /investigate` | Start an investigation session |
| `GET /snapshot/:container_id` | Capture container state for forking |
| `POST /remediate` | Fork a container with a strategy, run health check |
| `POST /plan` | Ask Claude to pick next strategies from error signatures |
| `POST /apply` | Apply winning strategy to production |
| `GET /card/:session_id` | Compressed FeatureCard summary |
| `GET /tree/:session_id` | Full fork decision tree |
| `GET /app/` | Decision tree UI — live polling, color-coded branch status |
| `GET /health` | Health check |

---

## Superplane Canvas

The canvas orchestrates the full 3-layer fork tree automatically.

**Setup:**
1. Import the canvas with the button above
2. Set canvas environment variables:
   - `FULCRUM_URL` — your deployed Fulcrum URL (e.g. `https://fulcrum.onrender.com`)
   - `SLACK_CHANNEL` — Slack channel ID for notifications
3. Copy the webhook URL from the canvas trigger node
4. Fire it:

```bash
curl -X POST <WEBHOOK_URL> \
  -H "Content-Type: application/json" \
  -d '{"container_id": "target-v2", "error_signature": "redis: ECONNREFUSED 127.0.0.1:6379"}'
```

---

## Baton (optional)

Baton tracks events and keeps a compressed FeatureCard across fork levels. Without it, Fulcrum runs with in-memory state only.

```bash
# Clone Baton alongside this repo
git clone https://github.com/eddie-nv/baton ../baton

# Start with Baton enabled
docker compose --profile baton up

# Set in .env
BATON_URL=http://localhost:3004
```

---

## Demo scenario

**The break:** `target:v2` points Redis at port 6379 (Redis is on 6380) and has no backoff on payment retries (provider rate-limits at 50%). Combined: ECONNREFUSED + retry flood → 503s.

**Resolution path:**
- Level 1 probes: rollback ✗, restart ✗, fix-redis-port ✗ (still 30% fail from rate limiting)
- Claude `/plan` → category: compound (config + dependency)
- Level 2: add-backoff ✗, add-circuit-breaker ✗, **fix-redis-port + add-backoff ✓**
- `/apply` → winner deployed

---

## Tests

```bash
# Unit tests (no Docker required)
pytest tests/test_api.py tests/test_strategy_registry.py tests/test_baton_client.py

# Integration tests (Docker + running containers)
pytest -m integration
```
