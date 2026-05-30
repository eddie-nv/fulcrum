"""Strategy registry — 40+ remediation strategies across 8 categories."""
from dataclasses import dataclass
from typing import Callable


@dataclass
class Strategy:
    name: str
    description: str
    category: str
    # Returns fork params dict: {"env_overrides": {...}} and optionally {"image": "..."}
    executor: Callable[[dict], dict]

    def get_fork_params(self, snapshot: dict) -> dict:
        return self.executor(snapshot)


def _env(**overrides) -> Callable[[dict], dict]:
    """Convenience: build an executor that applies static env overrides."""
    return lambda _snap: {"env_overrides": overrides}


def _rollback_image(suffix: str) -> Callable[[dict], dict]:
    """Build an executor that swaps an image suffix (e.g. -v2 → suffix)."""
    def executor(snap: dict) -> dict:
        image = snap.get("image", "")
        # Strip known version suffixes and append new one
        for old in ["-v2", "-v3", ":v2", ":v3", ":latest"]:
            if image.endswith(old):
                image = image[: -len(old)]
                break
        return {"image": image + suffix, "env_overrides": {}}
    return executor


REGISTRY: list[Strategy] = [
    # ── config ──────────────────────────────────────────────────────────────
    Strategy(
        name="fix-redis-port",
        description="Override REDIS_PORT to the correct value (6380)",
        category="config",
        executor=_env(REDIS_PORT="6380"),
    ),
    Strategy(
        name="fix-redis-host",
        description="Override REDIS_HOST to the correct service hostname",
        category="config",
        executor=_env(REDIS_HOST="redis"),
    ),
    Strategy(
        name="fix-payment-url",
        description="Override PAYMENT_URL to the correct endpoint",
        category="config",
        executor=_env(PAYMENT_URL="http://payment-provider:3003"),
    ),
    Strategy(
        name="fix-db-url",
        description="Override DATABASE_URL connection string to correct host/port",
        category="config",
        executor=_env(DATABASE_URL="postgres://localhost:5432/app"),
    ),
    Strategy(
        name="fix-port",
        description="Override application PORT to correct value (3000)",
        category="config",
        executor=_env(PORT="3000"),
    ),
    Strategy(
        name="disable-tls-verify",
        description="Disable TLS certificate verification for self-signed certs",
        category="config",
        executor=_env(NODE_TLS_REJECT_UNAUTHORIZED="0"),
    ),
    Strategy(
        name="use-env-defaults",
        description="Unset non-standard overrides and rely on service defaults",
        category="config",
        executor=lambda snap: {"env_overrides": {k: "" for k in snap.get("env", {}) if k.startswith("OVERRIDE_")}},
    ),

    # ── dependency ───────────────────────────────────────────────────────────
    Strategy(
        name="add-backoff",
        description="Enable exponential backoff on upstream retries",
        category="dependency",
        executor=_env(ENABLE_BACKOFF="true"),
    ),
    Strategy(
        name="add-circuit-breaker",
        description="Enable circuit breaker to stop retry storms",
        category="dependency",
        executor=_env(CIRCUIT_BREAKER="true", CIRCUIT_BREAKER_THRESHOLD="3"),
    ),
    Strategy(
        name="disable-retries",
        description="Disable all retries to fail fast and reduce load",
        category="dependency",
        executor=_env(MAX_PAYMENT_RETRIES="0"),
    ),
    Strategy(
        name="reduce-retries",
        description="Reduce max retries to 2 to limit retry flood",
        category="dependency",
        executor=_env(MAX_PAYMENT_RETRIES="2"),
    ),
    Strategy(
        name="reduce-max-retries",
        description="Set max retries to 1 as a tighter cap",
        category="dependency",
        executor=_env(MAX_PAYMENT_RETRIES="1"),
    ),
    Strategy(
        name="increase-timeout",
        description="Increase upstream request timeout to 10s",
        category="dependency",
        executor=_env(REQUEST_TIMEOUT="10000"),
    ),
    Strategy(
        name="add-retry-jitter",
        description="Enable jitter on retry delays to spread load",
        category="dependency",
        executor=_env(RETRY_JITTER="true", ENABLE_BACKOFF="true"),
    ),

    # ── runtime ──────────────────────────────────────────────────────────────
    Strategy(
        name="rollback",
        description="Roll back to the previous stable image tag",
        category="runtime",
        executor=_rollback_image("-v1"),
    ),
    Strategy(
        name="restart",
        description="Force a fresh container start with the same configuration",
        category="runtime",
        executor=lambda _snap: {"env_overrides": {}},
    ),
    Strategy(
        name="increase-memory",
        description="Increase container memory limit to 512m",
        category="runtime",
        executor=lambda snap: {"env_overrides": {}, "mem_limit": "512m"},
    ),
    Strategy(
        name="reduce-memory",
        description="Reduce memory limit to relieve host pressure",
        category="runtime",
        executor=lambda snap: {"env_overrides": {}, "mem_limit": "128m"},
    ),
    Strategy(
        name="enable-health-grace",
        description="Add a startup grace period before health checks begin",
        category="runtime",
        executor=_env(HEALTH_GRACE="30"),
    ),
    Strategy(
        name="reduce-workers",
        description="Reduce worker count to lower CPU and memory pressure",
        category="runtime",
        executor=_env(MAX_WORKERS="1"),
    ),

    # ── network ──────────────────────────────────────────────────────────────
    Strategy(
        name="fix-redis-host-dns",
        description="Use Redis IP address instead of hostname to bypass DNS",
        category="network",
        executor=_env(REDIS_HOST="127.0.0.1"),
    ),
    Strategy(
        name="fix-payment-host-dns",
        description="Use Payment provider IP instead of hostname",
        category="network",
        executor=_env(PAYMENT_URL="http://127.0.0.1:3003"),
    ),
    Strategy(
        name="enable-ipv4-only",
        description="Force IPv4 DNS resolution to avoid IPv6 routing issues",
        category="network",
        executor=_env(NODE_OPTIONS="--dns-result-order=ipv4first"),
    ),
    Strategy(
        name="increase-connect-timeout",
        description="Increase TCP connect timeout to 5s",
        category="network",
        executor=_env(CONNECT_TIMEOUT="5000"),
    ),
    Strategy(
        name="use-localhost-redis",
        description="Point Redis host to localhost (for sidecar deployments)",
        category="network",
        executor=_env(REDIS_HOST="127.0.0.1", REDIS_PORT="6380"),
    ),
    Strategy(
        name="disable-ipv6",
        description="Force pure IPv4 to avoid dual-stack routing failures",
        category="network",
        executor=_env(NODE_OPTIONS="--dns-result-order=ipv4first", DISABLE_IPV6="true"),
    ),

    # ── storage ──────────────────────────────────────────────────────────────
    Strategy(
        name="reduce-log-verbosity",
        description="Set log level to error-only to reduce disk writes",
        category="storage",
        executor=_env(LOG_LEVEL="error"),
    ),
    Strategy(
        name="disable-file-logging",
        description="Disable file-based logging to avoid disk exhaustion",
        category="storage",
        executor=_env(LOG_FILE="false"),
    ),
    Strategy(
        name="clear-cache",
        description="Disable in-process cache to free memory and disk",
        category="storage",
        executor=_env(CACHE_ENABLED="false"),
    ),
    Strategy(
        name="reduce-log-retention",
        description="Set log retention to 1 day to reclaim disk space",
        category="storage",
        executor=_env(LOG_RETENTION_DAYS="1"),
    ),

    # ── auth ─────────────────────────────────────────────────────────────────
    Strategy(
        name="rotate-api-key",
        description="Swap API_KEY to the secondary/backup credential",
        category="auth",
        executor=_env(API_KEY="backup-key"),
    ),
    Strategy(
        name="disable-auth-check",
        description="Disable auth middleware for isolated testing",
        category="auth",
        executor=_env(AUTH_ENABLED="false"),
    ),
    Strategy(
        name="refresh-auth-token",
        description="Force token refresh on next request",
        category="auth",
        executor=_env(TOKEN_REFRESH="true"),
    ),
    Strategy(
        name="increase-token-expiry",
        description="Extend token TTL to 24h to avoid mid-request expiry",
        category="auth",
        executor=_env(TOKEN_EXPIRY="86400"),
    ),

    # ── resource ─────────────────────────────────────────────────────────────
    Strategy(
        name="reduce-concurrency",
        description="Lower max concurrency to 2 to reduce resource contention",
        category="resource",
        executor=_env(MAX_CONCURRENT="2"),
    ),
    Strategy(
        name="increase-concurrency",
        description="Raise max concurrency to 10 for throughput-bound workloads",
        category="resource",
        executor=_env(MAX_CONCURRENT="10"),
    ),
    Strategy(
        name="reduce-rate-limit",
        description="Lower outbound rate limit to 10 req/s to respect upstream caps",
        category="resource",
        executor=_env(RATE_LIMIT="10"),
    ),
    Strategy(
        name="increase-rate-limit",
        description="Raise rate limit to 1000 req/s for high-throughput scenarios",
        category="resource",
        executor=_env(RATE_LIMIT="1000"),
    ),
    Strategy(
        name="increase-heap-size",
        description="Increase Node.js heap to 2GB to prevent OOM",
        category="resource",
        executor=_env(NODE_OPTIONS="--max-old-space-size=2048"),
    ),

    # ── code ─────────────────────────────────────────────────────────────────
    Strategy(
        name="rollback-to-v1",
        description="Force image to the v1 tag (known-good stable version)",
        category="code",
        executor=_rollback_image("-v1"),
    ),
    Strategy(
        name="enable-debug-mode",
        description="Enable debug logging to capture detailed error traces",
        category="code",
        executor=_env(DEBUG="true", LOG_LEVEL="debug"),
    ),
    Strategy(
        name="disable-feature-flags",
        description="Disable all experimental feature flags",
        category="code",
        executor=_env(FEATURE_FLAGS="none"),
    ),
    Strategy(
        name="use-previous-image",
        description="Run the :previous image tag (one deploy behind current)",
        category="code",
        executor=_rollback_image(":previous"),
    ),
]

_INDEX: dict[str, Strategy] = {s.name: s for s in REGISTRY}


def get(name: str) -> Strategy | None:
    return _INDEX.get(name)


def all_names() -> list[str]:
    return list(_INDEX.keys())


def by_category() -> dict[str, list[Strategy]]:
    result: dict[str, list[Strategy]] = {}
    for s in REGISTRY:
        result.setdefault(s.category, []).append(s)
    return result
