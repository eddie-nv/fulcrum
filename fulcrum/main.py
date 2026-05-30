import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

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


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/app/")


_UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")
if os.path.isdir(_UI_DIR):
    app.mount("/app", StaticFiles(directory=_UI_DIR, html=True), name="ui")
