import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.routers import local_models  # noqa: E402


def test_scan_local_models_requires_auth_header():
    app = FastAPI()
    app.include_router(local_models.router, prefix="/api")

    with TestClient(app) as client:
        response = client.get("/api/local-models/scan")

    assert response.status_code == 401
