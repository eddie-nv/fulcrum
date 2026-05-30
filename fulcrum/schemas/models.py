from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class StrategyStatus(str, Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"


class IncidentPayload(BaseModel):
    container_id: str = Field(..., description="ID or name of the broken container")
    error_signature: str = Field(..., description="Initial error description")
    metadata: dict[str, Any] = Field(default_factory=dict)


class InvestigateResponse(BaseModel):
    session_id: str
    container_id: str
    error_signature: str


class RemediateRequest(BaseModel):
    session_id: str
    strategy: str = Field(..., description="Strategy name to apply")
    snapshot: dict[str, Any] = Field(..., description="Container snapshot from ForkEngine")


class RemediateResponse(BaseModel):
    session_id: str
    strategy: str
    status: StrategyStatus
    error_signature: str | None = None
    passed: bool


class ApplyRequest(BaseModel):
    session_id: str
    strategy: str
    snapshot: dict[str, Any]


class ApplyResponse(BaseModel):
    session_id: str
    strategy: str
    applied: bool
    message: str


class PlanRequest(BaseModel):
    session_id: str
    error_signatures: list[str]
    tried_strategies: list[str] = Field(default_factory=list)
    level: int = Field(default=1, ge=1, le=3)


class PlanResponse(BaseModel):
    session_id: str
    category: str
    hypothesis: str
    confidence: float
    next_strategies: list[str]


class FeatureCard(BaseModel):
    session_id: str
    container_id: str
    status: str
    levels_tried: int
    winning_strategy: str | None = None
    error_signatures: list[str] = Field(default_factory=list)
    hypothesis: str | None = None
    open_blockers: list[str] = Field(default_factory=list)
    # Baton integration — set when BATON_URL is configured
    room_id: str | None = None


class BranchNode(BaseModel):
    id: str
    parent_id: str | None = None
    level: int
    strategy: str
    status: StrategyStatus
    error_signature: str | None = None


class BranchTree(BaseModel):
    session_id: str
    nodes: list[BranchNode]
