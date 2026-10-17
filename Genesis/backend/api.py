"""Public reads use frozen publications; operator reads require verified Firebase tokens."""
from pathlib import Path
from typing import Annotated

import firebase_admin
from firebase_admin import auth
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import GoogleAPICallError

from .config import Settings
from .dataset import DATASET_ID
from .engine import candidate_options, simulate
from .evolution import candidate_identity
from .models import CandidateFreezeRequest, DailyControlRequest, EvolutionRequest, FeedbackRequest, RecommendationReviewRequest, TriageRequest
from .jobs import run_evolution, run_local
from .dispatch import dispatch_configured, dispatch_run
from .usage import run_summary, summarize
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

    @app.middleware("http")
    async def private_cache_policy(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/api/operator/", "/api/admin/")):
            response.headers["Cache-Control"] = "no-store"
            response.headers.append("Vary", "Authorization")
        return response

    @app.exception_handler(Conflict)
    async def conflict_error(_request: Request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409, content={"detail": str(exc)})

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

    def admin(actor=Depends(operator)):
        if actor not in settings.admin_uids: raise HTTPException(403, "Admin account is not allowlisted")
        return actor

    @app.get("/api/demo/usage")
    def public_usage():
        return summarize(repo.usage_steps())

    @app.get("/api/operator/usage")
    def operator_usage(_actor=Depends(operator)):
        steps = repo.usage_steps()
        durations = [s["duration_ms"] for s in steps if s.get("duration_ms") is not None]
        return {**summarize(steps), "failed_attempts": sum(s["state"] in {"FAILED", "UNKNOWN_OUTCOME"} for s in steps),
            "retry_count": sum(s.get("attempt_number", 1) > 1 for s in steps),
            "mean_duration_ms": sum(durations) / len(durations) if durations else None, "daily": repo.daily_control()}

    @app.get("/api/operator/runs")
    def runs(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        page = repo.page("pipeline_runs", limit, cursor, [("dataset_id", DATASET_ID)], order="created_at")
        return {**page, "items": [run_summary(run) for run in page["items"]]}

    @app.get("/api/operator/runs/{run_id}")
    def run(run_id: str, actor=Depends(operator)):
        try: return {**repo.run_detail(run_id), "initiated_by_me": repo.get("pipeline_runs", run_id).get("actor_uid") == actor}
        except LookupError as exc: raise HTTPException(404, str(exc))

    @app.put("/api/admin/usage-daily")
    def daily_control(request: DailyControlRequest, actor=Depends(admin)):
        return repo.update_daily_control(request, actor)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": settings.mode, "live_ai_enabled": settings.live_ai,
            "dataset": "synthetic", "cloud_readiness": "UNVERIFIED"}

    @app.get("/api/config")
    def config():
        return {"mode": settings.mode, "project_id": settings.project_id,
            "auth_emulator_url": "http://" + settings.auth_host if settings.mode == "local" else None,
            "firebase_web_api_key": settings.firebase_web_api_key if settings.mode == "cloud" else None,
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
        return {"uid": actor, "mode": settings.mode, "is_admin": actor in settings.admin_uids, "live_ai_eligible": settings.ai_authorized()}

    @app.get("/api/operator/evaluation")
    def evaluation(_actor=Depends(operator)):
        data = repo.load_dataset()
        # This is a detector diagnostic, not evolution-driven candidate selection.
        return {"purpose": "BASELINE_DIAGNOSTIC", "selected_candidate": None,
            "candidates": candidate_options(), "discovery_preview": [simulate(data, candidate, "CALIBRATION_DISCOVERY") for candidate in candidate_options()],
            "freeze_options": [{"candidate": candidate, "candidate_hash": candidate_identity(data.manifest_hash, candidate)} for candidate in candidate_options()],
            "warning": "Synthetic discovery labels only. No candidate selected; held-out evaluation remains unopened."}

    @app.get("/api/operator/audit")
    def audit(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        return repo.page("audit_events", limit, cursor, order="occurred_at")

    @app.post("/api/operator/evolution/snapshots")
    def freeze_inputs(actor=Depends(operator)):
        return repo.freeze_analytical_inputs(actor)

    @app.post("/api/operator/evolution/runs")
    def enqueue_a5(request: EvolutionRequest, actor=Depends(operator)):
        if settings.mode != "local" and not dispatch_configured(settings):
            raise HTTPException(503, "Cloud dispatch is disabled or unverified")
        try:
            ident, created = repo.enqueue_evolution(request.snapshot_id, actor)
            if settings.mode == "cloud": dispatch_run(repo, ident)
            elif created and not settings.local_gemini_enabled: run_evolution(repo, ident)
            return repo.run_detail(ident)
        except LookupError as exc: raise HTTPException(404, str(exc))

    @app.get("/api/operator/evolution/runs/{run_id}")
    def a5_detail(run_id: str, _actor=Depends(operator)):
        try: return repo.evolution_detail(run_id)
        except LookupError as exc: raise HTTPException(404, str(exc))

    @app.get("/api/operator/evolution/runs")
    def a5_history(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        page = repo.page("pipeline_runs", limit, cursor, [("dataset_id", DATASET_ID), ("kind", "EVOLUTION")], order="created_at")
        return {**page, "items": [{**run_summary(run), "analytical_snapshot_id": run["analytical_snapshot_id"]} for run in page["items"]]}

    @app.put("/api/operator/evolution/recommendations/{recommendation_id}/review")
    def review_proposal(recommendation_id: str, request: RecommendationReviewRequest, actor=Depends(operator)):
        try: return repo.review_recommendation(recommendation_id, request, actor)
        except LookupError as exc: raise HTTPException(404, str(exc))

    @app.get("/api/operator/evolution/freeze")
    def frozen_candidate(_actor=Depends(operator)):
        from .dataset import stable_id
        frozen = repo.get("candidate_freezes", stable_id(DATASET_ID, "heldout"))
        return {"freeze": frozen, "simulation": repo.get("simulations", frozen["id"]) if frozen else None}

    @app.get("/api/operator/evolution/candidates")
    def freeze_options(_actor=Depends(operator)):
        manifest = repo.get("datasets", DATASET_ID)
        if not manifest or manifest.get("state") != "READY": raise HTTPException(409, "Dataset is not ready")
        return {"options": [{"candidate": candidate, "candidate_hash": candidate_identity(manifest["manifest_hash"], candidate)} for candidate in candidate_options()]}

    @app.post("/api/operator/evolution/freezes")
    def freeze_candidate(request: CandidateFreezeRequest, actor=Depends(operator)):
        return repo.freeze_candidate(request, actor)

    @app.post("/api/operator/evolution/freezes/{freeze_id}/simulation")
    def heldout(freeze_id: str, actor=Depends(operator)):
        try: return repo.simulate_frozen(freeze_id, actor)
        except LookupError as exc: raise HTTPException(404, str(exc))

    @app.get("/api/operator/evolution/snapshots")
    def input_history(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        return repo.page("analytical_snapshots", limit, cursor, [("dataset_id", DATASET_ID)], order="created_at")

    @app.post("/api/operator/alerts/{alert_id}/feedback")
    def feedback(alert_id: str, request: FeedbackRequest, actor=Depends(operator)):
        try: return repo.save_feedback(alert_id, request, actor)
        except LookupError as exc: raise HTTPException(404, str(exc))
        except Conflict as exc: raise HTTPException(409, str(exc))

    @app.post("/api/operator/triage-jobs")
    def triage(request: TriageRequest, actor=Depends(operator)):
        try:
            if settings.mode != "local" and not dispatch_configured(settings):
                raise HTTPException(503, "Cloud dispatch is disabled or unverified; no work enqueued")
            parent_id, created = repo.enqueue_triage(request.alert_ids, actor)
            if settings.mode == "cloud": dispatch_run(repo, parent_id)
            elif created and not settings.local_gemini_enabled: run_local(repo, parent_id)
            return {**repo.run_detail(parent_id), "initiated_by_me": repo.get("pipeline_runs", parent_id).get("actor_uid") == actor}
        except LookupError as exc: raise HTTPException(404, str(exc))
        except ValueError as exc: raise HTTPException(422, str(exc))

    @app.get("/api/operator/alerts/{alert_id}")
    def private_alert(alert_id: str, _actor=Depends(operator)):
        try: return repo.alert_detail(alert_id)
        except LookupError as exc: raise HTTPException(404, str(exc))
        except Conflict as exc: raise HTTPException(409, str(exc))

    @app.get("/api/operator/alerts/{alert_id}/feedback")
    def feedback_history(alert_id: str, _actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        if not repo.get("alerts", alert_id): raise HTTPException(404, "Alert not found")
        return repo.page("feedback_events", limit, cursor, [("alert_id", alert_id), ("dataset_id", DATASET_ID)], order="revision")

    dist = Path(__file__).resolve().parents[1] / "dist"
    if dist.exists(): app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
