from fastapi import APIRouter, HTTPException

from fulcrum.schemas.models import PlanRequest, PlanResponse
from fulcrum.services import ai_planner, session_store

router = APIRouter()


@router.post("/plan", response_model=PlanResponse)
async def plan(req: PlanRequest):
    card = session_store.get_card(req.session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")

    result, unmatched = ai_planner.plan(req, card)
    session_store.update_card(
        req.session_id,
        hypothesis=result.hypothesis,
        open_blockers=card.open_blockers + unmatched,
    )
    return result
