from fastapi import APIRouter, HTTPException
from fulcrum.schemas.models import PlanRequest, PlanResponse
from fulcrum.services import session_store

router = APIRouter()

# Stub strategy map — replaced by Claude API call in M4
_STUB_PLANS: dict[str, PlanResponse] = {}


def _stub_plan(req: PlanRequest) -> PlanResponse:
    """Hardcoded strategies for M2 stub. M4 replaces with Claude API."""
    sigs = " ".join(req.error_signatures).lower()

    if "redis" in sigs or "connection_refused" in sigs:
        strategies = ["fix-redis-port", "restart-redis", "increase-redis-timeout"]
        category = "config"
        hypothesis = "Redis connection misconfiguration causing cascade"
    elif "429" in sigs or "rate" in sigs:
        strategies = ["add-circuit-breaker", "add-backoff", "disable-retries"]
        category = "dependency"
        hypothesis = "Payment provider rate limiting without backoff causing retry flood"
    else:
        strategies = ["rollback", "restart", "reduce-resource-limits"]
        category = "runtime"
        hypothesis = "Unknown runtime failure — probing with general strategies"

    return PlanResponse(
        session_id=req.session_id,
        category=category,
        hypothesis=hypothesis,
        confidence=0.75,
        next_strategies=strategies,
    )


@router.post("/plan", response_model=PlanResponse)
async def plan(req: PlanRequest):
    card = session_store.get_card(req.session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")

    result = _stub_plan(req)
    session_store.update_card(req.session_id, hypothesis=result.hypothesis)
    return result
