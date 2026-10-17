"""Private authenticated task delivery; work runs in a bounded child process."""
import subprocess
import sys
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from .config import Settings
from .repository import Conflict, Repository


class Delivery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(pattern=r"^(?:[a-f0-9]{24}|[a-f0-9]{32})$")
    generation: StrictInt = Field(ge=1)


def execute_delivery(repo, lease):
    remaining = min(240, (lease.execution_deadline_at - datetime.now(timezone.utc)).total_seconds())
    if remaining <= 0: raise HTTPException(503, "WORKER_EXECUTION_BOUND")
    try:
        result = subprocess.run([sys.executable, "-m", "backend.jobs", "--delivery"],
            input=lease.model_dump_json(), text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parent.parent, timeout=remaining, check=False)
    except (subprocess.TimeoutExpired, OSError):
        # subprocess.run kills and waits on timeout. Preserve the lease/attempts;
        # redelivery after expiry recovers checkpoints without repeating unknown calls.
        raise HTTPException(503, "WORKER_INTERRUPTED") from None
    if result.returncode: raise HTTPException(503, "WORKER_INTERRUPTED")
    run = repo.get("pipeline_runs", lease.run_id)
    if not run or run.get("state") not in {"COMPLETE", "FAILED"}:
        raise HTTPException(503, "WORKER_NOT_TERMINAL")
    return {"status": "TERMINAL", "state": run["state"]}


def create_app(settings=None):
    settings = settings or Settings.load()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def private_response(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    def authenticate(request: Request):
        if not settings.worker_configured(): raise HTTPException(503, "WORKER_NOT_CONFIGURED")
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or len(header) > 16384:
            raise HTTPException(401, "TASK_IDENTITY_REQUIRED")
        try:
            claims = verify_oauth2_token(header[7:], partial(GoogleRequest(), timeout=10), settings.worker_audience)
        except (ValueError, GoogleAuthError):
            raise HTTPException(401, "TASK_IDENTITY_INVALID") from None
        if claims.get("email") != settings.task_invoker_email or claims.get("email_verified") is not True:
            raise HTTPException(403, "TASK_IDENTITY_FORBIDDEN")

    @app.post("/internal/jobs", dependencies=[Depends(authenticate)])
    def deliver(body: Delivery):
        try:
            repo = Repository(settings)
            claim = repo.claim_delivery(body.run_id, body.generation, uuid4().hex)
            if claim["status"] == "BUSY": raise HTTPException(503, "WORKER_LEASE_BUSY")
            if claim["status"] in {"STALE", "TERMINAL"}: return {"status": claim["status"]}
            return execute_delivery(repo, claim["lease"])
        except HTTPException: raise
        except Conflict:
            raise HTTPException(409, "WORKER_CLAIM_CONFLICT") from None
        except Exception:
            raise HTTPException(503, "WORKER_UNAVAILABLE") from None

    return app


app = create_app()
