# Fulcrum — Milestone Plan

## What it is

An AI incident response agent that runs parallel remediation attempts on isolated containers,
adapts its strategy based on error signatures, and hands off a compressed diagnosis — not a log
dump — when human action is required.

---

## Git flow (every milestone)

```
git checkout -b <branch>
# build
git add .
git commit -m "<message>"
git push -u origin <branch>
# open PR → merge → checkout main → git pull
```

---

## .claude folder structure (built up over milestones)

```
fulcrum/
  .claude/
    agents/
      planner.md
      architect.md
      fastapi-reviewer.md
      python-reviewer.md
      react-reviewer.md
      typescript-reviewer.md
      security-reviewer.md
      network-troubleshooter.md
      tdd-guide.md
      build-error-resolver.md
      react-build-resolver.md
      performance-optimizer.md
      code-reviewer.md
    skills/
      git-workflow/SKILL.md
      docker-patterns/SKILL.md
      fastapi-patterns/SKILL.md
      api-design/SKILL.md
      error-handling/SKILL.md
      backend-patterns/SKILL.md
      deployment-patterns/SKILL.md
      frontend-patterns/SKILL.md
```

---

## M1 — Project Foundation

**Branch:** `setup/project-foundation`

### Build
- `git init` inside `fulcrum/`, connect remote
- `CLAUDE.md` with project overview
- `.gitignore`
- `docker-compose.yml` with all four containers:
  - `target:v1` — healthy Express app (Redis on 6380, payment provider with backoff)
  - `target:v2` — broken (Redis pointed to wrong port 6379, no backoff on payment retries)
  - `redis` — running on port **6380**
  - `payment-provider` — returns 429 on 50% of requests deterministically
- `GET /health` on target service
- Verify broken scenario is reproducible

### .claude configs to add
```
.claude/agents/planner.md
.claude/agents/architect.md
.claude/skills/git-workflow/SKILL.md
.claude/skills/docker-patterns/SKILL.md
```

### Commit
```
git commit -m "setup: project foundation, docker infrastructure, target service containers"
```

---

## M2 — Fulcrum Core API

**Branch:** `feat/fulcrum-core-api`

### Build
- FastAPI app scaffold (`main.py`, `schemas/`, `services/`, `dependencies.py`)
- `POST /investigate` — intake incident payload, return `session_id` (stub Baton for now)
- `POST /remediate` — accept strategy + snapshot, return `{status, error_signature}`
- `POST /apply` — apply winning strategy to production container
- `POST /plan` — stub (returns hardcoded strategies for now)
- `GET /card/:session_id` — stub returning mock FeatureCard
- `GET /tree/:session_id` — stub returning mock branch tree
- `GET /health`
- Dockerfile for Fulcrum service
- Unit tests for each endpoint

### .claude configs to add
```
.claude/agents/fastapi-reviewer.md
.claude/agents/python-reviewer.md
.claude/agents/tdd-guide.md
.claude/skills/fastapi-patterns/SKILL.md
.claude/skills/api-design/SKILL.md
.claude/skills/error-handling/SKILL.md
.claude/skills/backend-patterns/SKILL.md
```

### Commit
```
git commit -m "feat: fulcrum fastapi service with stubbed endpoints"
```

---

## M3 — Docker Fork Engine

**Branch:** `feat/docker-fork-engine`

### Build
- `ForkEngine` class using Docker Python SDK
- `snapshot()` — captures image tag, env vars, resource limits, port bindings
- `fork(snapshot, strategy)` — spins up isolated test container with one modification
- `health_check(container)` — polls `GET /health`, returns `{passed, error_signature}`
- `teardown(container)` — kills and removes test container
- `fork_parallel(snapshot, strategies[])` — runs N forks concurrently, collects results
- Integration tests against the broken target service

### .claude configs to add
```
.claude/agents/security-reviewer.md
.claude/agents/build-error-resolver.md
```

### Commit
```
git commit -m "feat: docker fork engine — snapshot, parallel fork, health check, teardown"
```

---

## M4 — Strategy Library + AI Mapper

**Branch:** `feat/strategy-library`

### Build
- Strategy registry — 7 categories, 40+ strategies, each with:
  - `name`, `description`, `category`, `executor(snapshot) → modified_snapshot`
- Executor implementations (env var swaps, resource limit changes, image tag rollback, port corrections, etc.)
- `POST /plan` fully implemented:
  - Claude API call with error signatures + FeatureCard as input
  - Structured JSON output: `{category, hypothesis, confidence, next_strategies[]}`
  - Scorer: fuzzy match AI output to registered strategy names
  - Unmatched → `open_blocker` entry
- End-to-end test: broken target → level 1 probes → /plan → level 2 strategies generated correctly

### Strategy categories
| Category | Triggered when |
|---|---|
| `runtime` | OOMKill, crash loop, memory pressure |
| `code` | Rollback candidates, regression signals |
| `config` | Env var errors, wrong values |
| `network` | DNS errors, NXDOMAIN, connection refused |
| `storage` | ENOSPC, write errors, disk full |
| `auth` | 401, 403, token errors |
| `dependency` | Upstream timeout, 502, 503 |
| `resource` | CPU throttle, capacity limits |

### .claude configs to add
*(all already in place — no new configs for this milestone)*

### Commit
```
git commit -m "feat: strategy library (40+ strategies), AI mapper with Claude API, executor registry"
```

---

## M5 — Baton Integration

**Branch:** `feat/baton-integration`

### Build
- Baton client wrapper (calls Baton MCP tools via HTTP)
- Wire `/investigate` → `create_room` + `append_event` (session started)
- Wire each `/remediate` result → `append_event` (pass: `decision.made`, fail: `error.test`)
- Wire `/plan` → read FeatureCard before Claude call, write `hypothesis.raised` after
- Wire `/apply` → `append_event` (feature resolved or blocked)
- `GET /card/:session_id` → live FeatureCard from Baton (replace stub)
- `docker-compose.yml` — add Baton service + Redis
- End-to-end test: full run produces populated FeatureCard

### .claude configs to add
*(all already in place — no new configs for this milestone)*

### Commit
```
git commit -m "feat: baton integration — events, feature card, hypothesis tracking across forks"
```

---

## M6 — SuperPlane Canvas

**Branch:** `feat/superplane-canvas`

### Build
- Register at `app.superplane.com`, org: `hackatonsf-<team-name>`
- `canvas.yaml` — full workflow:
  - Webhook trigger → HTTP `/investigate`
  - Memory → store `session_id`
  - Runner ×3 parallel → HTTP `/remediate` (level 1 strategies)
  - HTTP → `/plan` (read error signatures)
  - Runner ×N parallel → HTTP `/remediate` (level 2 strategies)
  - Conditional → winner check
  - HTTP → `/apply`
  - Slack notification with FeatureCard summary
- `console.yaml` — Console component
- `README.md` with one-click canvas import button
- Manual test: trigger canvas against running broken target service

### .claude configs to add
*(architect.md and planner.md already in place — no new configs)*

### Commit
```
git commit -m "feat: superplane canvas and console yaml, readme import button"
```

---

## M7 — Decision Tree UI

**Branch:** `feat/decision-tree-ui`

### Build
- `GET /tree/:session_id` fully implemented in Fulcrum:
  - Returns JSON: `{nodes: [{id, parent_id, level, strategy, status, error_signature}]}`
- React + Vite app (`ui/`)
- `TreeView` component — top-down tree, nodes per level
- Node colors: gray (pending) / yellow (running) / green (pass) / red (fail)
- Hover tooltip showing error signature
- Live polling every 2 seconds while `status !== resolved`
- Auto-stops on resolution, shows final FeatureCard summary
- Served by Fulcrum on `GET /` or as static build

### .claude configs to add
```
.claude/agents/react-reviewer.md
.claude/agents/typescript-reviewer.md
.claude/agents/react-build-resolver.md
.claude/agents/performance-optimizer.md
.claude/skills/frontend-patterns/SKILL.md
```

### Commit
```
git commit -m "feat: decision tree UI — live polling, branch status, error signature tooltips"
```

---

## M8 — Render Deployment + Demo Polish

**Branch:** `feat/render-deployment`

### Build
- `render.yaml` — two services: Fulcrum web service + Redis instance
- Environment variables wired in Render dashboard
- Health check confirmed on Render URL
- Final end-to-end run: broken target → 3-layer fork → resolution → FeatureCard
- `README.md` final polish: description, demo GIF, import button, Render deploy button
- Confirm `canvas.yaml` + `console.yaml` importable cleanly

### .claude configs to add
```
.claude/agents/code-reviewer.md
.claude/skills/deployment-patterns/SKILL.md
```

### Commit
```
git commit -m "feat: render deployment config, final demo polish, readme"
```

---

## Demo scenario (Option A)

**The break:** `target:v2` runs with Redis pointed to port 6379 (Redis is on 6380) and no backoff
on retries to the payment provider which rate-limits at 50%. Combined: timeouts + retry flood → 503s.

**3-layer fork tree:**
```
[ payment-service: 503s ]
         │
 ┌───────┼───────┐                         LEVEL 1
[rollback] [restart] [config-fix]
  ✗         ✗ brief    ✗ partial
                        │
              AI /plan #1 → category: compound (redis + dependency)
                        │
     ┌──────────────────┼──────────────────┐   LEVEL 2
[fix-redis-port] [circuit-breaker-50] [disable-retries]
    ✗ still 30%fail   ✗ trips too late    ✗ fail fast but redis still slow
                        │
              AI /plan #2 → combine redis fix + circuit breaker
                        │
   ┌────────────────────┼────────────────────┐  LEVEL 3
[redis+cb-50]  [redis+cb-25]  [redis+disable-retries]
    ✗ marginal      ✓ PASSES        ✓ PASSES
                        │
                   /apply → winner
```

**Token comparison:**
| Approach | Tokens per fork |
|---|---|
| Full conversation replay | 15,000–50,000 |
| Fulcrum FeatureCard | 500 |
| Savings | 30–100x |
