# Fulcrum

An AI incident response agent that runs parallel remediation attempts on isolated containers, adapts its strategy based on error signatures, and hands off a compressed diagnosis — not a log dump — when human action is required.

## What it does

1. Receives an incident payload (`POST /investigate`)
2. Snapshots the broken container
3. Forks N isolated test containers, each with a different remediation strategy applied
4. Runs health checks in parallel, collects error signatures
5. Asks Claude to pick next strategies based on what failed and why (`POST /plan`)
6. Repeats across up to 3 levels of the fork tree
7. Applies the winning strategy to production (`POST /apply`)
8. Returns a compressed FeatureCard summary — not a raw log

## Architecture

| Component | Description |
|---|---|
| `fulcrum/` | FastAPI incident response API (Python) |
| `target/` | Express.js demo service (Node.js) |
| `payment-provider/` | Mock payment API — 50% 429 rate |
| `redis` | Cache — runs on port 6380 |

## Demo scenario

`target:v2` runs with Redis on wrong port (6379 instead of 6380) and no backoff on retries to the payment provider which rate-limits at 50%. Combined: timeouts + retry flood → 503s.

## Key ports

| Service | Port |
|---|---|
| target:v1 (healthy) | 3001 |
| target:v2 (broken) | 3002 |
| payment-provider | 3003 |
| redis | 6380 |
| fulcrum API | 8000 |

## Stack

- **Fulcrum**: FastAPI (Python 3.12), Docker Python SDK
- **Target service**: Express.js (Node.js 22)
- **AI**: Claude API (structured output)
- **Orchestration**: Superplane canvas
- **Deployment**: Render

## Development

```bash
docker compose up           # Start all services
docker compose logs -f target-v2   # Watch broken service
curl localhost:3001/health  # Should return 200
curl localhost:3002/health  # Should return 503
```
