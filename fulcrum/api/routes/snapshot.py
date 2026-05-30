import docker
from fastapi import APIRouter, HTTPException

from fulcrum.services.fork_engine import ForkEngine

router = APIRouter()


@router.get("/snapshot/{container_id}")
async def get_snapshot(container_id: str):
    """Return a ForkEngine snapshot of a running container."""
    try:
        engine = ForkEngine()
        return engine.snapshot(container_id)
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container '{container_id}' not found")
    except docker.errors.DockerException as exc:
        raise HTTPException(status_code=503, detail=f"Docker unavailable: {exc}")
