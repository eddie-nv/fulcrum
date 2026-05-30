"""Stub Baton client — replaced by real MCP integration in M5."""
import uuid
from fulcrum.schemas.models import StrategyStatus, BranchNode
from fulcrum.services import session_store


def remediate(session_id: str, strategy: str, snapshot: dict) -> tuple[bool, str | None]:
    """
    Stub: simulate a remediation attempt.
    Real implementation forks a container and checks health.
    Returns (passed, error_signature).
    """
    # Placeholder — M3 ForkEngine replaces this
    error_sig = f"stub:connection_refused (strategy={strategy})"
    passed = False
    node = BranchNode(
        id=str(uuid.uuid4()),
        level=1,
        strategy=strategy,
        status=StrategyStatus.failed,
        error_signature=error_sig,
    )
    session_store.append_node(session_id, node)
    return passed, error_sig
