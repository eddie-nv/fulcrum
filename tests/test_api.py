import pytest
from httpx import AsyncClient, ASGITransport
from fulcrum.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.anyio
async def test_investigate_creates_session(client):
    res = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: connection refused on port 6379",
    })
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["container_id"] == "target-v2"


@pytest.mark.anyio
async def test_remediate_unknown_session(client):
    res = await client.post("/remediate", json={
        "session_id": "nonexistent",
        "strategy": "fix-redis-port",
        "snapshot": {},
    })
    assert res.status_code == 404


@pytest.mark.anyio
async def test_remediate_returns_result(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: connection refused",
    })
    session_id = inv.json()["session_id"]

    res = await client.post("/remediate", json={
        "session_id": session_id,
        "strategy": "fix-redis-port",
        "snapshot": {"env": {"REDIS_PORT": "6379"}},
    })
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["strategy"] == "fix-redis-port"
    assert "passed" in data


@pytest.mark.anyio
async def test_plan_redis_signature(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: connection refused",
    })
    session_id = inv.json()["session_id"]

    res = await client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": ["redis: connection refused on port 6379"],
        "tried_strategies": [],
        "level": 1,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "config"
    assert "fix-redis-port" in data["next_strategies"]


@pytest.mark.anyio
async def test_plan_rate_limit_signature(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "payment: 429 rate limited",
    })
    session_id = inv.json()["session_id"]

    res = await client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": ["payment: 429 rate limited"],
        "tried_strategies": [],
        "level": 1,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "dependency"
    assert any("backoff" in s or "circuit" in s for s in data["next_strategies"])


@pytest.mark.anyio
async def test_apply_resolves_session(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: connection refused",
    })
    session_id = inv.json()["session_id"]

    res = await client.post("/apply", json={
        "session_id": session_id,
        "strategy": "fix-redis-port",
        "snapshot": {"env": {"REDIS_PORT": "6380"}},
    })
    assert res.status_code == 200
    assert res.json()["applied"] is True

    card = await client.get(f"/card/{session_id}")
    assert card.json()["status"] == "resolved"
    assert card.json()["winning_strategy"] == "fix-redis-port"


@pytest.mark.anyio
async def test_card_unknown_session(client):
    res = await client.get("/card/nonexistent")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_tree_returns_nodes_after_remediate(client):
    inv = await client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: connection refused",
    })
    session_id = inv.json()["session_id"]

    await client.post("/remediate", json={
        "session_id": session_id,
        "strategy": "fix-redis-port",
        "snapshot": {},
    })

    tree = await client.get(f"/tree/{session_id}")
    assert tree.status_code == 200
    nodes = tree.json()["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["strategy"] == "fix-redis-port"


@pytest.mark.anyio
async def test_apply_unknown_session(client):
    res = await client.post("/apply", json={
        "session_id": "nonexistent",
        "strategy": "fix-redis-port",
        "snapshot": {},
    })
    assert res.status_code == 404
