from fastapi import APIRouter, HTTPException

from fulcrum.schemas.models import PlanRequest, PlanResponse
from fulcrum.services import ai_planner, session_store
from fulcrum.services.baton_client import baton

router = APIRouter()


@router.post("/plan", response_model=PlanResponse)
async def plan(req: PlanRequest):
    card = session_store.get_card(req.session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enrich with Baton's resume packet before calling the AI planner —
    # it holds deduplicated failed-attempt signatures and prior hypotheses.
    if card.room_id:
        packet = await baton.get_resume_packet(card.room_id, req.session_id)
        if packet:
            failed_sigs = [
                fa["signature"]
                for fa in packet.get("failed_attempts", [])
                if fa.get("signature")
            ]
            if failed_sigs:
                merged = list(dict.fromkeys(req.error_signatures + failed_sigs))
                req = req.model_copy(update={"error_signatures": merged})
            if packet.get("open_blockers"):
                card = card.model_copy(update={"open_blockers": packet["open_blockers"]})

    result, unmatched = ai_planner.plan(req, card)

    # Record hypothesis to Baton
    if card.room_id:
        await baton.append_event(
            card.room_id,
            req.session_id,
            "hypothesis.raised",
            {"text": result.hypothesis, "confidence": result.confidence},
        )

    session_store.update_card(
        req.session_id,
        hypothesis=result.hypothesis,
        levels_tried=req.level,
        open_blockers=card.open_blockers + unmatched,
    )
    return result
