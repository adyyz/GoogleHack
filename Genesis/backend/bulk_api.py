"""Bounded corpus reads and explicit, operator-only durable batch actions."""
from typing import Annotated
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from google.cloud import firestore
from .bulk_dataset import ID, corpus
from .repository import Conflict
from . import bulk_jobs, bulk_learning, bulk_reference

Ident = Annotated[str, Field(pattern=r"^[a-f0-9]{24}$")]


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_ids: list[Ident] = Field(min_length=1, max_length=100)
    dataset_id: str = ID


class Start(Selection):
    selection_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,80}$")


class Revision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: Annotated[StrictInt, Field(ge=0)]


class BatchControl(Revision):
    acknowledge_failed: bool = False


def private_case(repo, ident):
    reference = bulk_reference.selected(ident)
    if reference: return {**corpus().case(ident), "reference_record": reference}
    worker = bulk_jobs.BulkRepository(repo.settings, ident)
    case = worker.materialize()
    existing = {r["id"]: r for r in worker.list("alerts")}
    for alert in case["alerts"]:
        row = existing[alert["id"]]
        alert.update(status=row["status"], frozen=row.get("feedback_revision", 0) > 0, applicable=True,
            actionable=not row.get("feedback_revision", 0) and row["status"] not in {"COMPLETE", "RUNNING", "QUEUED"})
    return case


def register(app, repo, operator):
    from .bulk_analytics import AnalyticsRepository
    from .intelligence_api import register as register_intelligence
    analytics = AnalyticsRepository(repo.settings)
    analytics.db = repo.db
    register_intelligence(app, analytics, operator, "/api/operator/bulk/evolution", "/api/demo/bulk/evolution")
    def invoke(call):
        try: return call()
        except LookupError as exc: raise HTTPException(404, str(exc))
        except ValueError as exc: raise HTTPException(422, str(exc))
        except Conflict as exc: raise HTTPException(409, str(exc))

    @app.get("/api/operator/seeded-history")
    def seeded_history(_actor=Depends(operator)):
        from .seeded_history import summary
        return invoke(lambda: summary(repo))

    @app.get("/api/operator/bulk/evolution/review-summary")
    def review_summary(_actor=Depends(operator)): return invoke(analytics.review_statistics)

    @app.get("/api/operator/bulk/evolution/snapshots")
    def snapshots(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = None):
        return repo.page("analytical_snapshots", limit, cursor, [("dataset_id", ID)], order="created_at")

    @app.get("/api/operator/bulk/evolution/patterns")
    def patterns(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = None):
        return repo.page("evolution_patterns", limit, cursor, [("dataset_id", ID)])

    @app.get("/api/operator/bulk/evolution/trends")
    def trends(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = None):
        from .rule_intelligence import review_trends
        return invoke(lambda: review_trends(analytics, limit, cursor))

    @app.get("/api/operator/bulk/evolution/observations")
    def observations(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, pattern=r"^[A-Za-z0-9_-]{1,128}$")):
        return invoke(lambda: analytics.observed_effects(limit, cursor))

    @app.get("/api/operator/cutoff-exercise")
    def exercise_state(_actor=Depends(operator)):
        from .cutoff_exercise import state
        return invoke(lambda: state(repo))

    @app.post("/api/operator/cutoff-exercise/{action}")
    def exercise_action(action: str, request: Revision, actor=Depends(operator)):
        from .cutoff_exercise import act
        return invoke(lambda: act(repo, action, request.expected_revision, actor))

    @app.get("/api/demo/bulk/summary")
    def summary():
        return invoke(lambda: {**corpus().summary(), "policy": bulk_learning.policy(repo), "provider_calls": 0,
            "genuine_human_reviews": 0, "population_fpr": None, "reference_fp_share": None})

    @app.get("/api/demo/bulk/reference-summary")
    def reference_summary(): return invoke(bulk_reference.summary)

    @app.get("/api/demo/bulk/cases")
    def cases(limit: int = Query(50, ge=1, le=100), cursor: int = Query(0, ge=0), identity: str = Query("", max_length=24),
              customer_type: str = Query("", pattern=r"^(|INDIVIDUAL|ORGANIZATION)$"), rule: str = Query("", max_length=40), q: str = Query("", max_length=100), status: str = Query("all", pattern=r"^(all|reference|awaiting_triage)$")):
        filters = dict(limit=limit, cursor=cursor, identity=identity, customer_type=customer_type, rule=rule, query=q)
        return invoke(lambda: bulk_reference.page(**filters) if status == "reference" else corpus().page(**filters) if status == "awaiting_triage" else bulk_reference.merge(corpus().page(**filters), **filters))

    @app.get("/api/operator/bulk/cases")
    def private_queue(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: int = Query(0, ge=0, le=40000), identity: str = Query("", max_length=24),
                      customer_type: str = Query("", pattern=r"^(|INDIVIDUAL|ORGANIZATION)$"), rule: str = Query("", max_length=40), q: str = Query("", max_length=100),
                      status: str = Query("all", pattern=r"^(all|reference|awaiting_triage|awaiting_review|frozen)$")):
        return invoke(lambda: bulk_jobs.queue(repo, limit=limit, cursor=cursor, identity=identity, customer_type=customer_type, rule=rule, query=q, status=status))

    @app.get("/api/demo/bulk/identities")
    def identities():
        def read():
            with corpus().connect() as db:
                return {"items": [dict(row) for row in db.execute("SELECT DISTINCT identity_id,name,customer_type FROM cases WHERE partition!='VALIDATION' ORDER BY name")]}
        return invoke(read)

    @app.get("/api/demo/bulk/cases/{ident}")
    def source_case(ident: Ident): return invoke(lambda: {**corpus().case(ident), "reference_record": bulk_reference.selected(ident)})

    @app.get("/api/operator/bulk/cases/{ident}")
    def operational_case(ident: Ident, _actor=Depends(operator)): return invoke(lambda: private_case(repo, ident))

    @app.get("/api/operator/bulk/summary")
    def operational_summary(_actor=Depends(operator)):
        def count(filters):
            query = repo.db.collection("alerts").where(filter=firestore.FieldFilter("dataset_id", "==", ID))
            for key, op, value in filters: query = query.where(filter=firestore.FieldFilter(key, op, value))
            return query.count().get(timeout=10)[0][0].value
        def verdict_count(verdict):
            return repo.db.collection("feedback_events").where(filter=firestore.FieldFilter("dataset_id", "==", ID)).where(filter=firestore.FieldFilter("verdict", "==", verdict)).count().get(timeout=10)[0][0].value
        def case_count(field):
            return repo.db.collection("bulk_case_progress").where(filter=firestore.FieldFilter("dataset_id", "==", ID)).where(filter=firestore.FieldFilter(field, "==", True)).count().get(timeout=10)[0][0].value
        return invoke(lambda: {"triaged_cases": case_count("triaged"), "reviewed_cases": case_count("reviewed"), "generated_source_alerts": sum(corpus().manifest["rule_alerts"].values()),
            "triaged_alerts": count([("status", "==", "COMPLETE")]), "reviewed_alerts": count([("feedback_revision", ">", 0)]),
            "true_positive": verdict_count("TRUE_POSITIVE"), "false_positive": verdict_count("FALSE_POSITIVE"), "inconclusive": verdict_count("INCONCLUSIVE"),
            "pending_case_denominator": corpus().manifest["eligible_pending_cases"]})

    @app.post("/api/operator/triage-batches/preview")
    def preview(request: Selection, actor=Depends(operator)):
        return invoke(lambda: bulk_jobs.preview(repo, request.case_ids, request.dataset_id, actor))

    @app.post("/api/operator/triage-batches")
    def start(request: Start, actor=Depends(operator)):
        return invoke(lambda: bulk_jobs.create(repo, request, actor))

    @app.get("/api/operator/triage-batches/{ident}")
    def detail(ident: Ident, _actor=Depends(operator)): return invoke(lambda: bulk_jobs.detail(repo, ident))

    @app.get("/api/operator/triage-batches")
    def batch_history(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = None):
        return invoke(lambda: repo.page("bulk_jobs", limit, cursor, [("dataset_id", ID)], order="created_at"))

    @app.post("/api/operator/triage-batches/{ident}/{action}")
    def control(ident: Ident, action: str, request: BatchControl, actor=Depends(operator)):
        return invoke(lambda: bulk_jobs.decision(repo, ident, request.expected_revision, action, actor, request.acknowledge_failed))

    @app.post("/api/operator/bulk/learning")
    def learn(actor=Depends(operator)): return invoke(lambda: bulk_learning.prepare(repo, actor))

    @app.get("/api/operator/bulk/learning")
    def history(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = None):
        return invoke(lambda: repo.page(bulk_learning.COLLECTION, limit, cursor, [("body.dataset_id", ID)]))

    @app.post("/api/operator/bulk/learning/{ident}/{action}")
    def learning_action(ident: Ident, action: str, request: Revision, actor=Depends(operator)):
        return invoke(lambda: bulk_learning.act(repo, ident, action, request.expected_revision, actor))

    @app.get("/api/operator/bulk/usage")
    def accounting(_actor=Depends(operator)):
        from .bulk_analytics import usage
        return invoke(lambda: usage(repo))

    @app.post("/api/operator/bulk/snapshots")
    def snapshot(actor=Depends(operator)):
        from .bulk_analytics import AnalyticsRepository
        return invoke(lambda: AnalyticsRepository(repo.settings).freeze_analytical_inputs(actor))

    class ReportRequest(BaseModel):
        model_config = ConfigDict(extra="forbid")
        snapshot_id: str = Field(pattern=r"^[a-f0-9]{64}$")

    @app.post("/api/operator/bulk/reports")
    def report(request: ReportRequest, actor=Depends(operator)):
        from .bulk_analytics import AnalyticsRepository
        def create_report():
            worker = AnalyticsRepository(repo.settings)
            ident, _created = worker.enqueue_evolution(request.snapshot_id, actor)
            if repo.settings.mode == "cloud":
                from .dispatch import dispatch_run
                dispatch_run(worker, ident)
            return worker.evolution_detail(ident)
        return invoke(create_report)

    @app.get("/api/operator/bulk/reports/{ident}")
    def read_report(ident: Ident, _actor=Depends(operator)):
        from .bulk_analytics import AnalyticsRepository
        return invoke(lambda: AnalyticsRepository(repo.settings).evolution_detail(ident))

    @app.get("/api/operator/bulk/reports")
    def report_history(_actor=Depends(operator), limit: int = Query(50, ge=1, le=100), cursor: str | None = None):
        return invoke(lambda: repo.page("pipeline_runs", limit, cursor, [("dataset_id", ID), ("kind", "EVOLUTION")], order="created_at"))
