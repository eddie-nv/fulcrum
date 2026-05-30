"""Docker Fork Engine — snapshot, fork, health check, teardown."""
import asyncio
import os
import time
import uuid

import docker
import httpx
from docker.models.containers import Container

HEALTH_PORT = 3000
HEALTH_PATH = "/health"
HEALTH_TIMEOUT_S = 30
HEALTH_POLL_INTERVAL_S = 1.0

_HTTPX_TRANSIENT = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
    httpx.ReadError,
)


def _is_inside_docker() -> bool:
    return os.path.exists("/.dockerenv")


def _parse_env(env_list: list[str]) -> dict[str, str]:
    env = {}
    for item in env_list or []:
        if "=" in item:
            k, v = item.split("=", 1)
            env[k] = v
    return env


def _extract_error_signature(errors: list | None, logs: str) -> str:
    if errors:
        return "; ".join(str(e) for e in errors[:3])
    lines = [ln.strip() for ln in logs.splitlines() if ln.strip()]
    error_lines = [
        ln for ln in lines
        if any(kw in ln.lower() for kw in ["error", "refused", "timeout", "429", "503", "econnrefused"])
    ]
    if error_lines:
        return error_lines[-1][:200]
    return lines[-1][:200] if lines else "fork:health_check_timeout"


class ForkEngine:
    def __init__(self, docker_client=None):
        self._client = docker_client or docker.from_env()

    def snapshot(self, container_id: str) -> dict:
        """Capture image, env vars, resource limits, and network from a running container."""
        c = self._client.containers.get(container_id)
        attrs = c.attrs
        config = attrs["Config"]
        host_config = attrs["HostConfig"]
        networks = list(attrs["NetworkSettings"]["Networks"].keys())
        return {
            "image": config["Image"],
            "env": _parse_env(config.get("Env") or []),
            "mem_limit": host_config.get("Memory") or None,
            "cpu_period": host_config.get("CpuPeriod") or None,
            "cpu_quota": host_config.get("CpuQuota") or None,
            "network": networks[0] if networks else "bridge",
            "original_name": attrs["Name"].lstrip("/"),
        }

    def fork(self, snapshot: dict, strategy: dict) -> Container:
        """Spin up an isolated test container with strategy modifications applied."""
        name = f"fulcrum-fork-{uuid.uuid4().hex[:8]}"
        env = {**snapshot["env"], **strategy.get("env_overrides", {})}
        image = strategy.get("image", snapshot["image"])

        container = self._client.containers.run(
            image=image,
            name=name,
            environment=env,
            network=snapshot["network"],
            # Always publish the health port — lets callers outside Docker reach it via localhost
            ports={f"{HEALTH_PORT}/tcp": None},
            detach=True,
            auto_remove=False,
            mem_limit=snapshot.get("mem_limit") or None,
        )
        return container

    def health_check(self, container: Container, timeout: int = HEALTH_TIMEOUT_S) -> tuple[bool, str | None]:
        """Poll GET /health until it returns 200 or timeout expires."""
        deadline = time.time() + timeout
        url = self._resolve_health_url(container)

        last_errors: list | None = None
        while time.time() < deadline:
            try:
                resp = httpx.get(url, timeout=3.0)
                if resp.status_code == 200:
                    return True, None
                try:
                    body = resp.json()
                    last_errors = body.get("errors")
                except Exception:
                    last_errors = [f"http:{resp.status_code}"]
            except _HTTPX_TRANSIENT:
                pass
            time.sleep(HEALTH_POLL_INTERVAL_S)

        try:
            logs = container.logs(tail=30).decode("utf-8", errors="replace")
        except Exception:
            logs = ""
        return False, _extract_error_signature(last_errors, logs)

    def teardown(self, container: Container) -> None:
        """Stop and remove the forked container."""
        try:
            container.stop(timeout=5)
        except Exception:
            pass
        try:
            container.remove(force=True)
        except Exception:
            pass

    def run_strategy(self, snapshot: dict, strategy: dict) -> tuple[bool, str | None]:
        """Fork → health_check → teardown. Returns (passed, error_signature)."""
        container = self.fork(snapshot, strategy)
        try:
            return self.health_check(container)
        finally:
            self.teardown(container)

    async def fork_parallel(self, snapshot: dict, strategies: list[dict]) -> list[dict]:
        """Run N strategy forks concurrently. Returns list of result dicts."""
        loop = asyncio.get_event_loop()

        async def _run_one(strategy: dict) -> dict:
            def _blocking():
                container = self.fork(snapshot, strategy)
                try:
                    passed, error_sig = self.health_check(container)
                finally:
                    self.teardown(container)
                return {
                    "strategy": strategy["name"],
                    "passed": passed,
                    "error_signature": error_sig,
                }
            return await loop.run_in_executor(None, _blocking)

        results = await asyncio.gather(*[_run_one(s) for s in strategies], return_exceptions=True)

        out = []
        for strategy, result in zip(strategies, results):
            if isinstance(result, Exception):
                out.append({
                    "strategy": strategy["name"],
                    "passed": False,
                    "error_signature": f"fork:exception:{type(result).__name__}:{result}",
                })
            else:
                out.append(result)
        return out

    def _resolve_health_url(self, container: Container) -> str:
        """Use internal IP when inside Docker; host-mapped port when outside."""
        container.reload()

        if _is_inside_docker():
            networks = container.attrs["NetworkSettings"]["Networks"]
            if networks:
                name = list(networks.keys())[0]
                ip = networks[name].get("IPAddress", "")
                if ip:
                    return f"http://{ip}:{HEALTH_PORT}{HEALTH_PATH}"

        # Outside Docker (or no internal IP): use host-mapped port
        ports = container.attrs["NetworkSettings"]["Ports"]
        bindings = ports.get(f"{HEALTH_PORT}/tcp") or []
        if bindings:
            return f"http://localhost:{bindings[0]['HostPort']}{HEALTH_PATH}"

        raise RuntimeError(f"Cannot determine health URL for container {container.name}")
