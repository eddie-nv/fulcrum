from fastapi import APIRouter, HTTPException
from fulcrum.schemas.models import RemediateRequest, RemediateResponse, StrategyStatus
from fulcrum.services import session_store, baton_stub

router = APIRouter()


@router.post("/remediate", response_model=RemediateResponse)
async def remediate(req: RemediateRequest):
    card = session_store.get_card(req.session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")

    passed, error_sig = baton_stub.remediate(
        session_id=req.session_id,
        strategy=req.strategy,
        snapshot=req.snapshot,
    )

    return RemediateResponse(
        session_id=req.session_id,
        strategy=req.strategy,
        status=StrategyStatus.passed if passed else StrategyStatus.failed,
        error_signature=error_sig,
        passed=passed,
    )
