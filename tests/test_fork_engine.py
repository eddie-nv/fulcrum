"""Integration tests for ForkEngine — require Docker + running target-v2."""
import pytest
import docker as docker_sdk

from fulcrum.services.fork_engine import ForkEngine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def docker_client():
    try:
        client = docker_sdk.from_env()
        client.ping()
        return client
    except Exception:
        pytest.skip("Docker not available")


@pytest.fixture(scope="module")
def engine(docker_client):
    return ForkEngine(docker_client=docker_client)


@pytest.fixture(scope="module")
def target_v2_snapshot(engine, docker_client):
    try:
        docker_client.containers.get("fulcrum-target-v2-1")
        container_name = "fulcrum-target-v2-1"
    except docker_sdk.errors.NotFound:
        try:
            docker_client.containers.get("target-v2")
            container_name = "target-v2"
        except docker_sdk.errors.NotFound:
            pytest.skip("target-v2 container not running — start with: docker compose up")
    return engine.snapshot(container_name)


def test_snapshot_captures_env(target_v2_snapshot):
    snap = target_v2_snapshot
    assert snap["image"]
    assert "REDIS_PORT" in snap["env"]
    assert snap["env"]["REDIS_PORT"] == "6379"
    assert snap["network"]


def test_snapshot_captures_broken_config(target_v2_snapshot):
    assert target_v2_snapshot["env"].get("ENABLE_BACKOFF") == "false"


def test_fork_broken_config_fails_health(engine, target_v2_snapshot):
    """Forking with the original broken config should fail health check."""
    strategy = {"name": "no-change", "env_overrides": {}}
    container = engine.fork(target_v2_snapshot, strategy)
    try:
        passed, error_sig = engine.health_check(container, timeout=20)
        assert not passed
        assert error_sig is not None
    finally:
        engine.teardown(container)


def test_fork_fix_redis_port_passes_health(engine, target_v2_snapshot):
    """Fixing REDIS_PORT to 6380 should make health check pass."""
    strategy = {"name": "fix-redis-port", "env_overrides": {"REDIS_PORT": "6380"}}
    container = engine.fork(target_v2_snapshot, strategy)
    try:
        passed, error_sig = engine.health_check(container, timeout=30)
        assert passed, f"Expected health check to pass, got error: {error_sig}"
    finally:
        engine.teardown(container)


def test_teardown_removes_container(engine, target_v2_snapshot, docker_client):
    strategy = {"name": "teardown-test", "env_overrides": {}}
    container = engine.fork(target_v2_snapshot, strategy)
    container_name = container.name
    engine.teardown(container)
    with pytest.raises(docker_sdk.errors.NotFound):
        docker_client.containers.get(container_name)


def test_run_strategy_convenience(engine, target_v2_snapshot):
    """run_strategy forks, checks health, and tears down — all in one call."""
    strategy = {"name": "fix-redis-port", "env_overrides": {"REDIS_PORT": "6380"}}
    passed, error_sig = engine.run_strategy(target_v2_snapshot, strategy)
    assert passed, f"Expected pass, got: {error_sig}"


@pytest.mark.anyio
async def test_fork_parallel_collects_results(engine, target_v2_snapshot):
    """fork_parallel runs strategies concurrently and returns one result per strategy."""
    strategies = [
        {"name": "no-change", "env_overrides": {}},
        {"name": "fix-redis-port", "env_overrides": {"REDIS_PORT": "6380"}},
    ]
    results = await engine.fork_parallel(target_v2_snapshot, strategies)
    assert len(results) == 2

    by_name = {r["strategy"]: r for r in results}
    assert not by_name["no-change"]["passed"]
    assert by_name["fix-redis-port"]["passed"]


@pytest.mark.anyio
async def test_fork_parallel_fix_backoff_fails(engine, target_v2_snapshot):
    """Fixing backoff alone (Redis still broken) should fail."""
    strategies = [
        {"name": "enable-backoff-only", "env_overrides": {"ENABLE_BACKOFF": "true"}},
    ]
    results = await engine.fork_parallel(target_v2_snapshot, strategies)
    assert len(results) == 1
    # Redis port is still wrong, so health check should fail
    assert not results[0]["passed"]
    assert results[0]["error_signature"] is not None
