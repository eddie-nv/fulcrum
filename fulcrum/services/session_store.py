import uuid
from fulcrum.schemas.models import FeatureCard, BranchNode


# In-memory store — replaced by Baton in M5
_sessions: dict[str, FeatureCard] = {}
_trees: dict[str, list[BranchNode]] = {}


def create_session(container_id: str, error_signature: str, room_id: str | None = None) -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = FeatureCard(
        session_id=session_id,
        container_id=container_id,
        status="investigating",
        levels_tried=0,
        error_signatures=[error_signature],
        room_id=room_id,
    )
    _trees[session_id] = []
    return session_id


def get_card(session_id: str) -> FeatureCard | None:
    return _sessions.get(session_id)


def get_tree(session_id: str) -> list[BranchNode] | None:
    if session_id not in _trees:
        return None
    return _trees[session_id]


def append_node(session_id: str, node: BranchNode) -> None:
    if session_id in _trees:
        _trees[session_id].append(node)


def update_card(session_id: str, **kwargs) -> FeatureCard | None:
    card = _sessions.get(session_id)
    if not card:
        return None
    _sessions[session_id] = card.model_copy(update=kwargs)
    return _sessions[session_id]
