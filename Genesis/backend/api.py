"""Public reads use frozen publications; operator reads require verified Firebase tokens."""
from pathlib import Path
from typing import Annotated

import firebase_admin
from firebase_admin import auth
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import GoogleAPICallError

from .config import Settings
from .engine import candidate_options, simulate
from .models import FeedbackRequest
from .repository import Conflict, Repository

ROLES = [
    {"id": 1, "name": "Evidence enrichment", "kind": "Deterministic", "output": "Transaction trail, facts, missing context", "used_by": "Risk assessment and investigation"},
    {"id": 2, "name": "Risk assessment", "kind": "Code + Gemini", "output": "Five scores and evidence-linked explanation", "used_by": "Categorization and analyst"},
    {"id": 3, "name": "Typology categorization", "kind": "Gemini", "output": "Typology and suggested action", "used_by": "Investigation brief and prioritization"},
    {"id": 4, "name": "Investigation brief", "kind": "Gemini", "output": "Findings, counter-evidence, next steps", "used_by": "Human analyst review"},
    {"id": 0, "name": "Post-triage prioritization", "kind": "Deterministic", "output": "Review priority with reasons", "used_by": "Analyst queue"},
    {"id": 5, "name": "Evolution intelligence", "kind": "Statistics + Gemini", "output": "Versioned improvement proposals and evaluation", "used_by": "Monitoring lead; approval required"},
]


def create_app(settings: Settings | None = None):
    settings = settings or Settings.load()
    repo = Repository(settings)
    app = FastAPI(title="AML Insight", version="0.1.0")
    firebase_app = firebase_admin.initialize_app(options={"projectId": settings.project_id}, name=f"api-{id(app)}")
    bearer = HTTPBearer(auto_error=False)

    @app.exception_handler(GoogleAPICallError)
    async def database_error(_request: Request, _exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"detail": "Database unavailable. Start the local emulators and seed the dataset."})

    def operator(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
        if not credentials: raise HTTPException(401, "Operator sign-in required")
        try:
            claims = auth.verify_id_token(credentials.credentials, app=firebase_app, check_revoked=True)
        except (ValueError, auth.InvalidIdTokenError, auth.RevokedIdTokenError, auth.UserDisabledError):
            raise HTTPException(401, "Invalid or expired operator token")
        if claims["uid"] not in settings.operator_uids: raise HTTPException(403, "Operator account is not allowlisted")
        return claims["uid"]

    def publication(response: Response):
        data = repo.publication()
        if not data: raise HTTPException(503, "No demonstration published. Seed the local dataset first.")
        response.headers["Cache-Control"] = "public, max-age=60"
        return data

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": settings.mode, "live_ai_enabled": settings.live_ai,
            "dataset": "synthetic", "cloud_readiness": "UNVERIFIED"}

    @app.get("/api/config")
    def config():
        return {"mode": settings.mode, "project_id": settings.project_id,
            "auth_emulator_url": "http://" + settings.auth_host if settings.mode == "local" else None,
            "live_ai_enabled": settings.live_ai}

    @app.get("/api/demo/manifest")
    def manifest(response: Response):
        data = publication(response)
        return {key: data[key] for key in ["id", "dataset_id", "snapshot_hash", "source_provenance", "published_at"]}

    @app.get("/api/demo/dashboard")
    def dashboard(response: Response):
        return publication(response)["public_summary"]

    @app.get("/api/demo/alerts")
    def alerts(response: Response):
        return {"cases": publication(response)["public_cases"]}

    @app.get("/api/demo/alerts/{case_id}")
    def detail(case_id: str, response: Response):
        for case in publication(response)["public_cases"]:
            if case["id"] == case_id: return case
        raise HTTPException(404, "Published case not found")

    @app.get("/api/system/agents")
    def agents():
        return {"roles": ROLES, "automatic_activation": False, "model_execution_status": "NOT_CONNECTED"}

    @app.get("/api/operator/session")
    def session(actor=Depends(operator)):
        return {"uid": actor, "mode": settings.mode}

    @app.get("/api/operator/evaluation")
    def evaluation(_actor=Depends(operator)):
        data = repo.load_dataset()
        # This is a detector diagnostic, not evolution-driven candidate selection.
        return {"purpose": "BASELINE_DIAGNOSTIC", "selected_candidate": None,
            "candidates": candidate_options(), "discovery_preview": [simulate(data, candidate, "CALIBRATION_DISCOVERY") for candidate in candidate_options()],
            "warning": "Synthetic discovery labels only. No candidate selected; held-out evaluation remains unopened."}

    @app.post("/api/operator/alerts/{alert_id}/feedback")
    def feedback(alert_id: str, request: FeedbackRequest, actor=Depends(operator)):
        try: return repo.save_feedback(alert_id, request, actor)
        except LookupError as exc: raise HTTPException(404, str(exc))
        except Conflict as exc: raise HTTPException(409, str(exc))

    @app.post("/api/operator/triage-jobs")
    def triage(_actor=Depends(operator)):
        raise HTTPException(503, "Live triage is not connected. Credit verification and the durable worker are required; no model request was sent.")

    dist = Path(__file__).resolve().parents[1] / "dist"
    if dist.exists(): app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
