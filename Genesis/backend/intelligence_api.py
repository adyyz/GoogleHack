"""Explicit operator actions for rule intelligence; public reads use reviewed publications."""
import re
from uuid import uuid4
from typing import Annotated
from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from google.cloud import firestore
from .dataset import DATASET_ID, content_hash
from .repository import Conflict, now
from .models import EvolutionRequest, RecommendationReviewRequest, PolicyChangeRequest, ReassessmentRequest
from . import calibration
from .rule_intelligence import catalog, matrix, operational_rows, statistics


class PublicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    report_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    executive_summary: str = Field(min_length=1, max_length=2000)


class WithdrawalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: Annotated[StrictInt, Field(ge=0)]
    notes: str = Field(min_length=1, max_length=2000)


def public_brief(repo):
    control = repo.get("evolution_publication_controls", DATASET_ID) or {"revision": 0, "publication_id": None}
    publication = repo.get("evolution_publications", control["publication_id"]) if control.get("publication_id") else None
    if publication and content_hash(publication["body"]) != publication["id"]: raise Conflict("Public brief integrity failed")
    return {"revision": control["revision"], "publication": publication}


def publication_body(repo, request):
    detail = repo.evolution_detail(request.report_id)
    if detail["run"]["state"] != "COMPLETE" or not detail.get("result"): raise Conflict("Completed genuine report required")
    summary = request.executive_summary.strip()
    if not summary or len(summary.split()) > 120 or re.search(r"[a-f0-9]{24,64}|AIza|Bearer |PRIVATE KEY", summary):
        raise ValueError("Public summary must be at most 120 words and contain no record identifiers or credentials")
    if any(row.get("display_name", "").lower() in summary.lower() for row in repo.list("customers") if row.get("display_name")):
        raise ValueError("Public summary must not identify individual cases or customers")
    snapshot = repo.get("analytical_snapshots", detail["analytical_snapshot_id"])
    if not snapshot or content_hash(snapshot["body"]) != detail["analytical_snapshot_id"]: raise Conflict("Frozen report inputs changed")
    from .models import EvolutionAssessment
    from .validation import validate_model_output
    validate_model_output(EvolutionAssessment.model_validate(detail["result"]), repo.evolution_context(detail["analytical_snapshot_id"]))
    computed = snapshot["body"].get("computed_statistics")
    if not computed: raise Conflict("Generate a versioned report with computed aggregate statistics before publishing")
    counts = {key: computed[key] for key in ("total_cases", "demo_cases", "total_alerts", "reviewed_cases", "reviewed_alerts", "true_positive", "false_positive", "inconclusive", "compared", "agreed", "suggestion_unavailable", "machine_uncertain")}
    body = {"executive_summary": summary, "counts": counts, "scope": "DEMO_AND_DISCOVERY",
        "source_report_id": request.report_id, "sample_note": "Human decisions on reviewed synthetic alerts; not population accuracy or FPR."}
    return body


def publish(repo, request, actor):
    body = publication_body(repo, request)
    ident = content_hash(body)
    @firestore.transactional
    def write(tx):
        ref = repo.db.collection("evolution_publication_controls").document(DATASET_ID)
        current = ref.get(transaction=tx)
        revision = current.to_dict()["revision"] if current.exists else 0
        version_ref = repo.db.collection("evolution_publications").document(ident)
        version = version_ref.get(transaction=tx)
        if revision != request.expected_revision: raise Conflict("Public brief changed; refresh")
        if version.exists and version.to_dict()["body"] != body: raise Conflict("Public version integrity failed")
        if not version.exists: tx.create(version_ref, {"id": ident, "dataset_id": DATASET_ID, "body": body, "published_at": now()})
        tx.set(ref, {"revision": revision + 1, "publication_id": ident})
        tx.create(repo.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
            "action": "EVOLUTION_SUMMARY_PUBLISHED", "object_collection": "evolution_publications", "object_id": ident,
            "actor": actor, "occurred_at": now()})
        return {"publication_id": ident, "revision": revision + 1}
    return repo._contended_transaction(write)


def withdraw(repo, request, actor):
    @firestore.transactional
    def write(tx):
        ref = repo.db.collection("evolution_publication_controls").document(DATASET_ID)
        current = ref.get(transaction=tx)
        row = current.to_dict() if current.exists else {"revision": 0}
        if row["revision"] != request.expected_revision: raise Conflict("Public brief changed; refresh")
        tx.set(ref, {"revision": row["revision"] + 1, "publication_id": None})
        tx.create(repo.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
            "action": "EVOLUTION_SUMMARY_WITHDRAWN", "object_collection": "evolution_publications",
            "object_id": row.get("publication_id"), "actor": actor, "notes": request.notes, "occurred_at": now()})
        return {"revision": row["revision"] + 1, "publication": None}
    return repo._contended_transaction(write)


def register(app, repo, operator):
    def invoke(call):
        try: return call()
        except LookupError as exc: raise HTTPException(404, str(exc))
        except ValueError as exc: raise HTTPException(422, str(exc))

    @app.get("/api/demo/rules")
    def public_rules(): return {"rules": catalog()}

    @app.get("/api/demo/evolution/brief")
    def published(response: Response):
        response.headers["Cache-Control"] = "no-store"
        return public_brief(repo)

    @app.get("/api/operator/evolution/rule-matrix")
    def rule_matrix(_actor=Depends(operator)): return invoke(lambda: matrix(repo))

    @app.get("/api/operator/cases/{case_id}")
    def private_case(case_id: str, _actor=Depends(operator)):
        def read():
            source = repo.operational_case(case_id)
            queue = repo.operator_queue("discovery" if source["split"] == "CALIBRATION_DISCOVERY" else "demo")
            return next(row for row in queue["cases"] if row["id"] == case_id)
        return invoke(read)

    @app.get("/api/operator/evolution/rules/{rule_id}/examples")
    def examples(rule_id: str, _actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        cases, _, alerts, feedback, _ = operational_rows(repo)
        ids = {row["id"] for row in alerts if row["rule_id"] == rule_id}
        page = repo.page("feedback_events", limit, cursor, [("dataset_id", DATASET_ID)], order="submitted_at")
        cases = {row["id"]: row for row in cases}
        return {**page, "items": [{"feedback": row, "case": cases[row["case_id"]]} for row in page["items"] if row["alert_id"] in ids]}

    @app.get("/api/operator/evolution/auto-label/policy")
    def label_policy(_actor=Depends(operator)): return calibration.active_label_policy(repo)

    @app.post("/api/operator/evolution/auto-label/calibrations")
    def prepare_labels(request: EvolutionRequest, actor=Depends(operator)):
        return invoke(lambda: calibration.prepare(repo, request.snapshot_id, actor))

    @app.get("/api/operator/evolution/auto-label/calibrations")
    def calibrations(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        return repo.page("auto_label_calibrations", limit, cursor, [("dataset_id", DATASET_ID)], order="created_at")

    @app.get("/api/operator/evolution/auto-label/candidates")
    def candidates(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        return {**repo.page("auto_label_candidates", limit, cursor, [("dataset_id", DATASET_ID)], order="frozen_at"), "active_policy": calibration.active_label_policy(repo)}

    @app.post("/api/operator/evolution/auto-label/candidates/{ident}/validate")
    def validate(ident: str, actor=Depends(operator)): return invoke(lambda: calibration.validate_candidate(repo, ident, actor))

    @app.put("/api/operator/evolution/auto-label/candidates/{ident}/review")
    def review(ident: str, request: RecommendationReviewRequest, actor=Depends(operator)):
        return invoke(lambda: calibration.decision(repo, ident, request, actor, "review"))

    @app.post("/api/operator/evolution/auto-label/candidates/{ident}/apply")
    def apply(ident: str, request: PolicyChangeRequest, actor=Depends(operator)):
        return invoke(lambda: calibration.decision(repo, ident, request, actor, "apply"))

    @app.post("/api/operator/evolution/auto-label/candidates/{ident}/rollback")
    def rollback(ident: str, request: PolicyChangeRequest, actor=Depends(operator)):
        return invoke(lambda: calibration.decision(repo, ident, request, actor, "rollback"))

    @app.post("/api/operator/evolution/auto-label/candidates/{ident}/reassess")
    def reassess(ident: str, request: ReassessmentRequest, actor=Depends(operator)):
        return invoke(lambda: calibration.reassess(repo, ident, request, actor))

    @app.get("/api/operator/evolution/auto-label/assessments")
    def assessments(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        return repo.page("auto_label_assessments", limit, cursor, [("dataset_id", DATASET_ID)], order="created_at")

    @app.get("/api/operator/evolution/public-brief")
    def brief(_actor=Depends(operator)): return public_brief(repo)

    @app.post("/api/operator/evolution/public-brief")
    def publication(request: PublicationRequest, actor=Depends(operator)): return invoke(lambda: publish(repo, request, actor))

    @app.post("/api/operator/evolution/public-brief/preview")
    def preview(request: PublicationRequest, _actor=Depends(operator)):
        return invoke(lambda: {"body": publication_body(repo, request)})

    @app.post("/api/operator/evolution/public-brief/withdraw")
    def withdrawal(request: WithdrawalRequest, actor=Depends(operator)): return withdraw(repo, request, actor)
