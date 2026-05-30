from fastapi import APIRouter, HTTPException

from fulcrum.schemas.models import BranchTree, FeatureCard
from fulcrum.services import session_store
from fulcrum.services.baton_client import baton

router = APIRouter()


def _merge_baton_card(card: FeatureCard, live: dict) -> FeatureCard:
    """Apply relevant fields from Baton's live FeatureCard onto Fulcrum's card."""
    updates: dict = {}

    # Map Baton state → Fulcrum status
    state_map = {"merged": "resolved", "blocked": "blocked", "abandoned": "failed"}
    if live.get("state") in state_map:
        updates["status"] = state_map[live["state"]]

    # Latest hypothesis text
    hypotheses = live.get("hypotheses") or []
    if hypotheses:
        updates["hypothesis"] = hypotheses[-1].get("text", card.hypothesis)

    # Deduplicated error signatures from failed attempts
    failed_sigs = [fa["signature"] for fa in live.get("failed_attempts", []) if fa.get("signature")]
    if failed_sigs:
        merged = list(dict.fromkeys(card.error_signatures + failed_sigs))
        updates["error_signatures"] = merged

    # Open blockers
    if live.get("open_blockers"):
        updates["open_blockers"] = live["open_blockers"]

    return card.model_copy(update=updates) if updates else card


@router.get("/card/{session_id}", response_model=FeatureCard)
async def get_card(session_id: str):
    card = session_store.get_card(session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enrich with live Baton data when available
    if card.room_id:
        live = await baton.get_feature_card(card.room_id, session_id)
        if live:
            card = _merge_baton_card(card, live)

    return card


@router.get("/tree/{session_id}", response_model=BranchTree)
async def get_tree(session_id: str):
    nodes = session_store.get_tree(session_id)
    if nodes is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return BranchTree(session_id=session_id, nodes=nodes)
