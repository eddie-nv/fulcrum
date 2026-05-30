from fastapi import APIRouter, HTTPException
from fulcrum.schemas.models import FeatureCard, BranchTree
from fulcrum.services import session_store

router = APIRouter()


@router.get("/card/{session_id}", response_model=FeatureCard)
async def get_card(session_id: str):
    card = session_store.get_card(session_id)
    if not card:
        raise HTTPException(status_code=404, detail="Session not found")
    return card


@router.get("/tree/{session_id}", response_model=BranchTree)
async def get_tree(session_id: str):
    nodes = session_store.get_tree(session_id)
    if nodes is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return BranchTree(session_id=session_id, nodes=nodes)
