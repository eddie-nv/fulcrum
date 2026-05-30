"""AI Planner — Claude API call to select remediation strategies."""
import json
import os
from difflib import get_close_matches

from fulcrum.schemas.models import FeatureCard, PlanRequest, PlanResponse
from fulcrum.services import strategy_registry

_TOOL_SCHEMA = {
    "name": "submit_plan",
    "description": "Submit the incident remediation plan",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Root cause category (config, dependency, runtime, network, storage, auth, resource, code)",
            },
            "hypothesis": {
                "type": "string",
                "description": "1–2 sentence root cause hypothesis",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score 0.0–1.0",
            },
            "next_strategies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of strategy names to try next (from the registry)",
            },
        },
        "required": ["category", "hypothesis", "confidence", "next_strategies"],
    },
}

_SYSTEM = """\
You are Fulcrum's AI incident response planner. You analyze container health check failures and \
select remediation strategies from the provided registry to try next.

Rules:
- Only suggest strategy names that appear in the registry (exact match preferred)
- Pick 2–4 strategies most likely to fix the observed error signatures
- Avoid strategies already tried
- Order by descending confidence
- If root cause spans multiple categories (compound failure), include strategies from each
"""


def _build_registry_context() -> str:
    sections = []
    for category, strategies in strategy_registry.by_category().items():
        lines = [f"### {category}"]
        for s in strategies:
            lines.append(f"- `{s.name}`: {s.description}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def _build_user_message(req: PlanRequest, card: FeatureCard) -> str:
    tried = ", ".join(req.tried_strategies) if req.tried_strategies else "none"
    sigs = "\n".join(f"- {s}" for s in req.error_signatures)
    prior = card.hypothesis or "none"

    return f"""\
## Incident Context
Session: {req.session_id}
Container: {card.container_id}
Level: {req.level} of 3
Prior hypothesis: {prior}

## Error Signatures
{sigs}

## Already Tried
{tried}

## Strategy Registry
{_build_registry_context()}

Analyze the error signatures and call `submit_plan` with your diagnosis."""


def _score_strategies(names: list[str]) -> tuple[list[str], list[str]]:
    """Match Claude's suggestions against registered names. Returns (matched, unmatched)."""
    registered = strategy_registry.all_names()
    matched: list[str] = []
    unmatched: list[str] = []
    seen: set[str] = set()
    for name in names:
        name = name.strip()
        if name in registered and name not in seen:
            matched.append(name)
            seen.add(name)
            continue
        close = get_close_matches(name, registered, n=1, cutoff=0.6)
        if close and close[0] not in seen:
            matched.append(close[0])
            seen.add(close[0])
        else:
            unmatched.append(name)
    return matched, unmatched


def _stub_plan(req: PlanRequest) -> tuple[PlanResponse, list[str]]:
    """Heuristic fallback when ANTHROPIC_API_KEY is not set."""
    sigs = " ".join(req.error_signatures).lower()

    if "redis" in sigs or "connection" in sigs or "6379" in sigs:
        strategies = ["fix-redis-port", "restart-redis", "increase-connect-timeout"]
        category = "config"
        hypothesis = "Redis connection misconfiguration causing cascade failures"
    elif "429" in sigs or "rate" in sigs:
        strategies = ["add-backoff", "add-circuit-breaker", "disable-retries"]
        category = "dependency"
        hypothesis = "Payment provider rate limiting without backoff causing retry flood"
    else:
        strategies = ["rollback", "restart", "reduce-resource-limits"]
        category = "runtime"
        hypothesis = "Unknown runtime failure — probing with general strategies"

    tried = set(req.tried_strategies)
    strategies = [s for s in strategies if s not in tried]
    matched, unmatched = _score_strategies(strategies)
    return PlanResponse(
        session_id=req.session_id,
        category=category,
        hypothesis=hypothesis,
        confidence=0.75,
        next_strategies=matched,
    ), unmatched


def plan(req: PlanRequest, card: FeatureCard) -> tuple[PlanResponse, list[str]]:
    """
    Call Claude to select next strategies. Returns (PlanResponse, unmatched_strategy_names).
    Falls back to heuristic stub when ANTHROPIC_API_KEY is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _stub_plan(req)

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "submit_plan"},
            messages=[{"role": "user", "content": _build_user_message(req, card)}],
        )

        tool_use = next(b for b in response.content if b.type == "tool_use")
        result: dict = tool_use.input

        matched, unmatched = _score_strategies(result["next_strategies"])
        return PlanResponse(
            session_id=req.session_id,
            category=result["category"],
            hypothesis=result["hypothesis"],
            confidence=float(result["confidence"]),
            next_strategies=matched,
        ), unmatched

    except Exception:
        # Any API/parse error → fall back to stub so the service stays up
        return _stub_plan(req)
