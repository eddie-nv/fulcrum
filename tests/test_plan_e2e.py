"""
End-to-end integration tests for the AI planner.

Requires:
- Docker + running target-v2 container (for ForkEngine snapshots)
- ANTHROPIC_API_KEY set (for real Claude calls)

Run with: pytest -m integration tests/test_plan_e2e.py
"""
import os
import pytest
import docker as docker_sdk
from httpx import AsyncClient, ASGITransport

from fulcrum.main import app
from fulcrum.services import strategy_registry
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
def base_snapshot(engine, docker_client):
    for name in ("fulcrum-target-v2-1", "target-v2"):
        try:
            docker_client.containers.get(name)
            return engine.snapshot(name)
        except docker_sdk.errors.NotFound:
            continue
    pytest.skip("target-v2 container not running")


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_plan_with_redis_error_suggests_config_strategies(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: connect ECONNREFUSED 127.0.0.1:6379",
    })
    session_id = inv.json()["session_id"]

    res = await client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": ["redis: connect ECONNREFUSED 127.0.0.1:6379"],
        "tried_strategies": [],
        "level": 1,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["category"] in ("config", "network")
    assert data["hypothesis"]
    assert 0 < data["confidence"] <= 1.0
    assert len(data["next_strategies"]) >= 1
    # All returned strategies must be in the registry
    for name in data["next_strategies"]:
        assert strategy_registry.get(name) is not None, f"Unknown strategy returned: {name}"


@pytest.mark.anyio
async def test_plan_with_rate_limit_error_suggests_dependency_strategies(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "payment: 429 Too Many Requests",
    })
    session_id = inv.json()["session_id"]

    res = await client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": ["payment: 429 Too Many Requests"],
        "tried_strategies": [],
        "level": 1,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "dependency"
    names = data["next_strategies"]
    assert any(n in names for n in ("add-backoff", "add-circuit-breaker", "disable-retries", "reduce-retries"))


@pytest.mark.anyio
async def test_plan_avoids_already_tried_strategies(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED",
    })
    session_id = inv.json()["session_id"]

    res = await client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": ["redis: ECONNREFUSED"],
        "tried_strategies": ["fix-redis-port", "fix-redis-host"],
        "level": 2,
    })
    assert res.status_code == 200
    data = res.json()
    # Should not re-suggest strategies already tried
    for tried in ["fix-redis-port", "fix-redis-host"]:
        assert tried not in data["next_strategies"]


@pytest.mark.anyio
async def test_plan_compound_failure_level2_suggests_combined_strategies(client):
    """Level 2 with both redis and rate-limit errors should suggest combined strategies."""
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED; payment: 429",
    })
    session_id = inv.json()["session_id"]

    res = await client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": [
            "redis: connect ECONNREFUSED 127.0.0.1:6379",
            "payment: 429 Too Many Requests",
        ],
        "tried_strategies": ["fix-redis-port"],
        "level": 2,
    })
    assert res.status_code == 200
    data = res.json()
    # Should suggest at least 2 strategies across categories
    assert len(data["next_strategies"]) >= 2
    for name in data["next_strategies"]:
        assert strategy_registry.get(name) is not None


@pytest.mark.anyio
async def test_plan_updates_feature_card_hypothesis(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED",
    })
    session_id = inv.json()["session_id"]

    await client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": ["redis: ECONNREFUSED"],
        "tried_strategies": [],
        "level": 1,
    })

    card = await client.get(f"/card/{session_id}")
    assert card.status_code == 200
    assert card.json()["hypothesis"] is not None


@pytest.mark.anyio
async def test_full_e2e_level1_fork_then_plan_then_level2(engine, base_snapshot, client):
    """
    Full flow: /investigate → fork level 1 probes → /plan → verify level 2 strategies.
    """
    # Create session
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED; payment: 429",
    })
    session_id = inv.json()["session_id"]

    # Level 1: run three probes in parallel
    level1_strategies = [
        {"name": "rollback", **strategy_registry.get("rollback").get_fork_params(base_snapshot)},
        {"name": "restart", **strategy_registry.get("restart").get_fork_params(base_snapshot)},
        {"name": "fix-redis-port", **strategy_registry.get("fix-redis-port").get_fork_params(base_snapshot)},
    ]
    level1_results = await engine.fork_parallel(base_snapshot, level1_strategies)

    # Record results — all three should fail (redis only partially fixed)
    error_sigs = [r["error_signature"] for r in level1_results if r["error_signature"]]
    tried = [r["strategy"] for r in level1_results]

    # /plan call with level 1 results
    plan_res = await client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": error_sigs or ["redis: ECONNREFUSED", "payment: 429"],
        "tried_strategies": tried,
        "level": 2,
    })
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert len(plan_data["next_strategies"]) >= 1
    for name in plan_data["next_strategies"]:
        assert strategy_registry.get(name) is not None, f"Unregistered strategy: {name}"
