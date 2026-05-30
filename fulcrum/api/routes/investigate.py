from fastapi import APIRouter

from fulcrum.schemas.models import IncidentPayload, InvestigateResponse
from fulcrum.services import session_store
from fulcrum.services.baton_client import baton

router = APIRouter()


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate(payload: IncidentPayload):
    # Create Baton room for this incident session
    room_result = await baton.create_room(title=f"incident/{payload.container_id}")
    room_id = room_result["room_id"] if room_result else None

    session_id = session_store.create_session(
        container_id=payload.container_id,
        error_signature=payload.error_signature,
        room_id=room_id,
    )

    # Record investigation start as a branch event
    if room_id:
        await baton.append_event(
            room_id,
            session_id,
            "action.branch",
            {
                "branch": f"incident/{payload.container_id}",
                "parent_branch": "production",
                "base_sha": f"container:{payload.container_id}",
            },
        )

    return InvestigateResponse(
        session_id=session_id,
        container_id=payload.container_id,
        error_signature=payload.error_signature,
    )
