from fastapi import APIRouter, HTTPException

from fulcrum.schemas.models import ApplyRequest, ApplyResponse
from fulcrum.services import session_store
from fulcrum.services.baton_client import baton

router = APIRouter()


@router.post("/apply", response_model=ApplyResponse)
async def apply(req: ApplyRequest):
    card = session_store.get_card(req.session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")

    session_store.update_card(
        req.session_id,
        status="resolved",
        winning_strategy=req.strategy,
    )

    # Record resolution to Baton — decision.made clears hypotheses and marks the feature done
    if card.room_id:
        await baton.append_event(
            card.room_id,
            req.session_id,
            "decision.made",
            {
                "summary": f"Resolved: strategy '{req.strategy}' applied to {card.container_id}",
                "next_action": "monitor production health",
            },
        )

    return ApplyResponse(
        session_id=req.session_id,
        strategy=req.strategy,
        applied=True,
        message=f"Strategy '{req.strategy}' applied to production container {card.container_id}",
    )
