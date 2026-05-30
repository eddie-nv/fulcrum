from fastapi import FastAPI
from fulcrum.api.routes import health, investigate, remediate, apply, plan, card, snapshot

app = FastAPI(
    title="Fulcrum",
    description="AI incident response agent — parallel container remediation",
    version="0.1.0",
)

app.include_router(health.router, tags=["health"])
app.include_router(investigate.router, tags=["investigate"])
app.include_router(snapshot.router, tags=["snapshot"])
app.include_router(remediate.router, tags=["remediate"])
app.include_router(apply.router, tags=["apply"])
app.include_router(plan.router, tags=["plan"])
app.include_router(card.router, tags=["card"])
