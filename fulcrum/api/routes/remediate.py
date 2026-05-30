import uuid

import docker
from fastapi import APIRouter, HTTPException

from fulcrum.schemas.models import BranchNode, RemediateRequest, RemediateResponse, StrategyStatus
from fulcrum.services import baton_stub, session_store
from fulcrum.services.baton_client import baton
from fulcrum.services.fork_engine import ForkEngine

router = APIRouter()


def _short_signature(error_sig: str | None) -> str:
    if not error_sig:
        return "unknown"
    sig = error_sig.lower()
    for kw in ("econnrefused", "timeout", "429", "503", "oom", "refused", "reset"):
        if kw in sig:
            return kw
    return sig[:40].replace(" ", "_")


@router.post("/remediate", response_model=RemediateResponse)
async def remediate(req: RemediateRequest):
    card = session_store.get_card(req.session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")

    snapshot = req.snapshot

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

    # Record fork result to Baton
    if card.room_id:
        if passed:
            await baton.append_event(
                card.room_id,
                req.session_id,
                "decision.made",
                {
                    "summary": f"Strategy '{req.strategy}' passed health check",
                    "next_action": f"apply {req.strategy} to production",
                },
            )
        else:
            await baton.append_event(
                card.room_id,
                req.session_id,
                "error.test",
                {
                    "test_name": req.strategy,
                    "output": error_sig or "health check failed",
                    "signature": _short_signature(error_sig),
                },
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
