"""Baton client — event-sourcing state fabric for incident sessions.

Calls POST /api/mcp/:tool with Bearer <room_id> auth.
Returns None gracefully on any failure or when BATON_URL is not set.
"""
import os

import httpx

BATON_URL = os.getenv("BATON_URL", "")
BATON_ACTOR_ID = os.getenv("BATON_ACTOR_ID", "fulcrum")


class BatonClient:
    def __init__(self, base_url: str = "", actor_id: str = BATON_ACTOR_ID):
        self.base_url = (base_url or BATON_URL).rstrip("/")
        self.actor_id = actor_id

    @property
    def available(self) -> bool:
        return bool(self.base_url)

    async def _call(self, tool: str, room_id: str | None, payload: dict) -> dict | None:
        if not self.available:
            return None
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if room_id:
            headers["Authorization"] = f"Bearer {room_id}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/mcp/{tool}",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            return None

    async def create_room(self, title: str) -> dict | None:
        """Create a new room for an incident session. Returns {room_id, project_id}."""
        return await self._call("create_room", None, {"title": title})

    async def append_event(
        self,
        room_id: str,
        feature_id: str,
        event_type: str,
        payload: dict,
    ) -> dict | None:
        """Append an event to the feature's event stream."""
        return await self._call(
            "append_event",
            room_id,
            {
                "room_id": room_id,
                "feature_id": feature_id,
                "type": event_type,
                "payload": payload,
                "actor_id": self.actor_id,
            },
        )

    async def get_feature_card(self, room_id: str, feature_id: str) -> dict | None:
        """Fetch the live FeatureCard (<= 500 tokens) from Baton."""
        return await self._call(
            "get_feature_card",
            room_id,
            {"room_id": room_id, "feature_id": feature_id},
        )

    async def get_resume_packet(self, room_id: str, feature_id: str) -> dict | None:
        """Fetch the ResumePacket (<= 1500 tokens) for AI context."""
        return await self._call(
            "get_resume_packet",
            room_id,
            {"room_id": room_id, "feature_id": feature_id},
        )


# Module-level singleton — routes import this directly
baton = BatonClient()
