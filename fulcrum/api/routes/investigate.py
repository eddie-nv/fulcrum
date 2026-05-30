from fastapi import APIRouter, HTTPException
from fulcrum.schemas.models import IncidentPayload, InvestigateResponse
from fulcrum.services import session_store

router = APIRouter()


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate(payload: IncidentPayload):
    session_id = session_store.create_session(
        container_id=payload.container_id,
        error_signature=payload.error_signature,
    )
    return InvestigateResponse(
        session_id=session_id,
        container_id=payload.container_id,
        error_signature=payload.error_signature,
    )
