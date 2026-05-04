import logging
import os
import asyncio
from typing import Dict, Any, Optional

import httpx
from fastapi import APIRouter, Depends

from app.core.response import ok
from app.routers.auth_db import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/local-models", tags=["本地模型"])


def _is_docker() -> bool:
    return os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER") == "1"


async def _scan_service(base_url: str, timeout: float = 3.0) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{base_url}/v1/models")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                return {
                    "available": True,
                    "base_url": base_url,
                    "models": [
                        {"id": m.get("id", ""), "object": m.get("object", "model")}
                        for m in models
                    ],
                }
            return {"available": False, "base_url": base_url, "models": [], "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"available": False, "base_url": base_url, "models": [], "error": str(e)}


@router.get("/scan")
async def scan_local_models(current_user: dict = Depends(get_current_user)):
    is_docker = _is_docker()

    ollama_url = (
        "http://host.docker.internal:11434" if is_docker
        else "http://localhost:11434"
    )
    lmstudio_url = (
        "http://host.docker.internal:1234" if is_docker
        else "http://localhost:1234"
    )

    ollama_result, lmstudio_result = await asyncio.gather(
        _scan_service(ollama_url),
        _scan_service(lmstudio_url),
    )

    return ok(data={
        "docker_environment": is_docker,
        "ollama": ollama_result,
        "lmstudio": lmstudio_result,
    })
