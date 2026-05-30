"""Unit and integration tests for the Baton client and M5 route wiring."""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from fulcrum.main import app
from fulcrum.services.baton_client import BatonClient


# ── Unit tests — no network required ─────────────────────────────────────────

def test_client_unavailable_when_no_url():
    client = BatonClient(base_url="")
    assert not client.available


def test_client_available_when_url_set():
    client = BatonClient(base_url="http://localhost:3004")
    assert client.available


@pytest.mark.anyio
async def test_create_room_returns_none_when_unavailable():
    client = BatonClient(base_url="")
    assert await client.create_room("test") is None


@pytest.mark.anyio
async def test_append_event_returns_none_when_unavailable():
    client = BatonClient(base_url="")
    result = await client.append_event("room1", "feat1", "error.test", {})
    assert result is None


@pytest.mark.anyio
async def test_get_feature_card_returns_none_when_unavailable():
    client = BatonClient(base_url="")
    assert await client.get_feature_card("room1", "feat1") is None


@pytest.mark.anyio
async def test_get_resume_packet_returns_none_when_unavailable():
    client = BatonClient(base_url="")
    assert await client.get_resume_packet("room1", "feat1") is None


@pytest.mark.anyio
async def test_create_room_returns_none_on_http_error():
    client = BatonClient(base_url="http://localhost:9999")  # nothing listening
    result = await client.create_room("test")
    assert result is None


# ── Route wiring — verify graceful no-Baton operation ────────────────────────

@pytest.fixture
async def api_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_investigate_creates_session_without_baton(api_client):
    res = await api_client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED",
    })
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    # room_id is absent in card when Baton is not configured
    card = await api_client.get(f"/card/{data['session_id']}")
    assert card.status_code == 200
    assert card.json()["room_id"] is None


@pytest.mark.anyio
async def test_investigate_stores_room_id_when_baton_returns_one(api_client):
    mock_result = {"room_id": "room-abc", "project_id": "proj-1"}
    with patch("fulcrum.api.routes.investigate.baton.create_room", new=AsyncMock(return_value=mock_result)):
        with patch("fulcrum.api.routes.investigate.baton.append_event", new=AsyncMock(return_value={})):
            res = await api_client.post("/investigate", json={
                "container_id": "target-v2",
                "error_signature": "redis: ECONNREFUSED",
            })
    assert res.status_code == 200
    session_id = res.json()["session_id"]
    card = await api_client.get(f"/card/{session_id}")
    assert card.json()["room_id"] == "room-abc"


@pytest.mark.anyio
async def test_remediate_appends_error_test_on_failure(api_client):
    inv = await api_client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED",
    })
    session_id = inv.json()["session_id"]

    append_mock = AsyncMock(return_value={})
    with patch("fulcrum.api.routes.remediate.baton.append_event", new=append_mock):
        # Inject a room_id into the card so the baton path runs
        from fulcrum.services import session_store
        session_store.update_card(session_id, room_id="room-xyz")

        await api_client.post("/remediate", json={
            "session_id": session_id,
            "strategy": "fix-redis-port",
            "snapshot": {},
        })

    # Should have called append_event with error.test (stub always fails)
    calls = [call.args for call in append_mock.call_args_list]
    event_types = [c[2] for c in calls]
    assert "error.test" in event_types


@pytest.mark.anyio
async def test_plan_appends_hypothesis_raised(api_client):
    inv = await api_client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED",
    })
    session_id = inv.json()["session_id"]

    from fulcrum.services import session_store
    session_store.update_card(session_id, room_id="room-xyz")

    append_mock = AsyncMock(return_value={})
    resume_mock = AsyncMock(return_value=None)
    with patch("fulcrum.api.routes.plan.baton.append_event", new=append_mock):
        with patch("fulcrum.api.routes.plan.baton.get_resume_packet", new=resume_mock):
            await api_client.post("/plan", json={
                "session_id": session_id,
                "error_signatures": ["redis: ECONNREFUSED"],
                "tried_strategies": [],
                "level": 1,
            })

    calls = [call.args for call in append_mock.call_args_list]
    event_types = [c[2] for c in calls]
    assert "hypothesis.raised" in event_types


@pytest.mark.anyio
async def test_apply_appends_decision_made(api_client):
    inv = await api_client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED",
    })
    session_id = inv.json()["session_id"]

    from fulcrum.services import session_store
    session_store.update_card(session_id, room_id="room-xyz")

    append_mock = AsyncMock(return_value={})
    with patch("fulcrum.api.routes.apply.baton.append_event", new=append_mock):
        res = await api_client.post("/apply", json={
            "session_id": session_id,
            "strategy": "fix-redis-port",
            "snapshot": {},
        })

    assert res.status_code == 200
    calls = [call.args for call in append_mock.call_args_list]
    event_types = [c[2] for c in calls]
    assert "decision.made" in event_types


@pytest.mark.anyio
async def test_get_card_merges_baton_state(api_client):
    inv = await api_client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED",
    })
    session_id = inv.json()["session_id"]

    from fulcrum.services import session_store
    session_store.update_card(session_id, room_id="room-xyz")

    live_baton_card = {
        "state": "merged",
        "hypotheses": [{"text": "Redis port misconfiguration", "confidence": 0.9}],
        "failed_attempts": [{"signature": "econnrefused", "test_name": "no-change"}],
        "open_blockers": [],
    }
    with patch("fulcrum.api.routes.card.baton.get_feature_card", new=AsyncMock(return_value=live_baton_card)):
        card = await api_client.get(f"/card/{session_id}")

    assert card.status_code == 200
    data = card.json()
    assert data["status"] == "resolved"
    assert data["hypothesis"] == "Redis port misconfiguration"
    assert "econnrefused" in data["error_signatures"]


@pytest.mark.anyio
async def test_plan_enriches_error_sigs_from_resume_packet(api_client):
    inv = await api_client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED",
    })
    session_id = inv.json()["session_id"]

    from fulcrum.services import session_store
    session_store.update_card(session_id, room_id="room-xyz")

    resume_packet = {
        "failed_attempts": [
            {"signature": "econnrefused", "test_name": "rollback"},
            {"signature": "429", "test_name": "restart"},
        ],
        "open_blockers": [],
    }
    append_mock = AsyncMock(return_value={})
    with patch("fulcrum.api.routes.plan.baton.get_resume_packet", new=AsyncMock(return_value=resume_packet)):
        with patch("fulcrum.api.routes.plan.baton.append_event", new=append_mock):
            res = await api_client.post("/plan", json={
                "session_id": session_id,
                "error_signatures": ["redis: ECONNREFUSED"],
                "tried_strategies": [],
                "level": 1,
            })

    assert res.status_code == 200


# ── Integration tests — require live Baton at BATON_URL ──────────────────────

pytestmark_integration = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.anyio
async def test_full_baton_flow(api_client):
    baton_url = os.getenv("BATON_URL")
    if not baton_url:
        pytest.skip("BATON_URL not set — start Baton with: docker compose --profile baton up")

    # Full round-trip: investigate → plan → apply → get card
    inv = await api_client.post("/investigate", json={
        "container_id": "target-v2",
        "error_signature": "redis: ECONNREFUSED 127.0.0.1:6379",
    })
    assert inv.status_code == 200
    session_id = inv.json()["session_id"]

    card = await api_client.get(f"/card/{session_id}")
    assert card.status_code == 200
    assert card.json()["room_id"] is not None

    plan_res = await api_client.post("/plan", json={
        "session_id": session_id,
        "error_signatures": ["redis: ECONNREFUSED 127.0.0.1:6379"],
        "tried_strategies": [],
        "level": 1,
    })
    assert plan_res.status_code == 200

    apply_res = await api_client.post("/apply", json={
        "session_id": session_id,
        "strategy": plan_res.json()["next_strategies"][0],
        "snapshot": {},
    })
    assert apply_res.status_code == 200

    # Card should reflect resolution from Baton
    final_card = await api_client.get(f"/card/{session_id}")
    assert final_card.status_code == 200
    data = final_card.json()
    assert data["hypothesis"] is not None
