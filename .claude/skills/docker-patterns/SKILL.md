---
name: docker-patterns
description: Docker and Docker Compose patterns for local development, container security, networking, volume strategies, and multi-service orchestration.
origin: ECC
---

# Docker Patterns

Docker and Docker Compose best practices for containerized development.

## When to Activate

- Setting up Docker Compose for local development
- Designing multi-container architectures
- Troubleshooting container networking or volume issues
- Reviewing Dockerfiles for security and size
- Migrating from local dev to containerized workflow

## Docker Compose for Local Development

### Standard Multi-Service Stack

```yaml
services:
  app:
    build:
      context: .
      target: dev
    ports:
      - "3000:3000"
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - DATABASE_URL=postgres://postgres:postgres@db:5432/app_dev
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

  db:
    image: postgres:16-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Multi-Stage Dockerfile

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app

FROM base AS dev
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0"]

FROM base AS production
RUN addgroup --gid 1001 appgroup && adduser --uid 1001 --gid 1001 appuser
COPY --chown=appuser:appgroup requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appgroup . .
USER appuser
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:8000/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Networking

### Service Discovery

Services in the same Compose network resolve by service name:
```
redis://redis:6379        # "redis" resolves to the redis container
postgres://db:5432/app    # "db" resolves to the db container
```

### Custom Networks

```yaml
services:
  api:
    networks:
      - frontend-net
      - backend-net
  db:
    networks:
      - backend-net    # Only reachable from api

networks:
  frontend-net:
  backend-net:
```

## Debugging

```bash
# View logs
docker compose logs -f app
docker compose logs --tail=50 redis

# Shell into container
docker compose exec app sh
docker compose exec app bash

# Check DNS resolution inside container
docker compose exec app nslookup redis

# Check connectivity
docker compose exec app wget -qO- http://target:3000/health

# Inspect network
docker network ls
docker network inspect <project>_default

# Resource usage
docker stats

# Rebuild
docker compose up --build
docker compose build --no-cache app

# Clean up
docker compose down
docker compose down -v    # Also removes volumes (DESTRUCTIVE)
```

## Container Security

```dockerfile
# 1. Use specific tags
FROM python:3.12.3-slim

# 2. Run as non-root
RUN addgroup --gid 1001 app && adduser --uid 1001 --gid 1001 app
USER app

# 3. No secrets in image layers
# Never: ENV API_KEY=sk-xxx
```

```yaml
# Compose security
services:
  app:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

## Secret Management

```yaml
# GOOD: env_file (never commit .env)
services:
  app:
    env_file:
      - .env

# BAD: hardcoded in compose or Dockerfile
# environment:
#   - API_KEY=sk-xxx
```

## .dockerignore

```
__pycache__
*.pyc
.venv
.env
.env.*
.git
*.log
node_modules
dist
coverage
```

## Anti-Patterns

- Using `:latest` tag — pin to specific versions
- Running as root — always create non-root user
- Storing data in containers without volumes — ephemeral
- Putting secrets in docker-compose.yml — use .env files
- One giant container with all services — one process per container
