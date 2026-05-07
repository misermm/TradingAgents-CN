from fastapi import APIRouter, Request
import time
from pathlib import Path

router = APIRouter()


def get_version() -> str:
    try:
        version_file = Path(__file__).parent.parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding='utf-8').strip()
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"读取VERSION文件失败: {e}")
    return "0.1.16"


async def _check_mongodb() -> dict:
    try:
        from app.core.database import get_mongo_client
        client = get_mongo_client()
        if client is None:
            return {"status": "unavailable"}
        t0 = time.monotonic()
        await client.admin.command('ping')
        latency = (time.monotonic() - t0) * 1000
        return {"status": "ok", "latency_ms": round(latency, 1)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_redis() -> dict:
    try:
        from app.core.database import get_redis_client
        client = get_redis_client()
        if client is None:
            return {"status": "unavailable"}
        t0 = time.monotonic()
        await client.ping()
        latency = (time.monotonic() - t0) * 1000
        return {"status": "ok", "latency_ms": round(latency, 1)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_scheduler() -> dict:
    try:
        from app.services.scheduler_service import get_scheduler_service
        svc = get_scheduler_service()
        scheduler = svc.scheduler
        if scheduler and scheduler.running:
            return {"status": "ok"}
        return {"status": "stopped"}
    except Exception:
        return {"status": "unavailable"}


@router.get("/health")
async def health(request: Request):
    components = {
        "mongodb": await _check_mongodb(),
        "redis": await _check_redis(),
        "scheduler": _check_scheduler(),
    }

    all_ok = all(
        c.get("status") in ("ok", "stopped")
        for c in components.values()
    )
    critical_ok = all(
        c.get("status") == "ok"
        for k, c in components.items()
        if k in ("mongodb", "redis")
    )

    status = "ok" if all_ok else "degraded"
    ready = critical_ok

    uptime_seconds = None
    start_time = getattr(request.app.state, "start_time", None)
    if start_time:
        uptime_seconds = round(time.time() - start_time, 1)

    message = "服务运行正常" if ready else "服务启动中，部分组件不可用"

    return {
        "success": True,
        "data": {
            "status": status,
            "ready": ready,
            "version": get_version(),
            "timestamp": int(time.time()),
            "service": "TradingAgents-CN API",
            "uptime_seconds": uptime_seconds,
            "components": components,
        },
        "message": message,
    }


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz")
async def readyz():
    mongodb = await _check_mongodb()
    redis = await _check_redis()
    ready = mongodb.get("status") == "ok" and redis.get("status") == "ok"
    return {"ready": ready}
