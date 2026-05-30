import uuid

import docker
from fastapi import APIRouter, HTTPException

from fulcrum.schemas.models import BranchNode, RemediateRequest, RemediateResponse, StrategyStatus
from fulcrum.services import baton_stub, session_store
from fulcrum.services.fork_engine import ForkEngine

router = APIRouter()


@router.post("/remediate", response_model=RemediateResponse)
async def remediate(req: RemediateRequest):
    card = session_store.get_card(req.session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")

    snapshot = req.snapshot

    # Use ForkEngine when snapshot carries a full container state (has "image").
    # Fall back to stub for unit tests that pass a minimal snapshot dict.
    if "image" in snapshot:
        try:
            engine = ForkEngine()
            strategy = {
                "name": req.strategy,
                "env_overrides": snapshot.get("env_overrides", {}),
            }
            if "image" in strategy.get("env_overrides", {}):
                strategy["image"] = strategy["env_overrides"].pop("image")
            passed, error_sig = engine.run_strategy(snapshot, strategy)
        except docker.errors.DockerException as exc:
            passed, error_sig = False, f"fork:docker_error:{exc}"
    else:
        passed, error_sig = baton_stub.remediate(
            session_id=req.session_id,
            strategy=req.strategy,
            snapshot=snapshot,
        )

    node = BranchNode(
        id=str(uuid.uuid4()),
        level=1,
        strategy=req.strategy,
        status=StrategyStatus.passed if passed else StrategyStatus.failed,
        error_signature=error_sig,
    )
    session_store.append_node(req.session_id, node)

    return RemediateResponse(
        session_id=req.session_id,
        strategy=req.strategy,
        status=StrategyStatus.passed if passed else StrategyStatus.failed,
        error_signature=error_sig,
        passed=passed,
    )
