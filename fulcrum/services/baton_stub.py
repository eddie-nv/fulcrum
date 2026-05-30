"""Stub Baton client — replaced by real MCP integration in M5."""


def remediate(session_id: str, strategy: str, snapshot: dict) -> tuple[bool, str | None]:
    """Stub: simulate a failed remediation. ForkEngine handles real runs."""
    return False, f"stub:connection_refused (strategy={strategy})"
