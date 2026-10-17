"""Firestore is the only mutable application store; no in-memory verdict registry."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from random import uniform
from time import sleep

import google.auth.credentials
from google.api_core.exceptions import Aborted
from google.cloud import firestore

from .config import Settings
from .dataset import DATASET_ID, content_hash, stable_id
from .models import Account, Case, Customer, Dataset, PipelineRun, StepRun, Transaction, UsageDaily, WorkerLease, retry_allowed


def now():
    return datetime.now(timezone.utc)


class Conflict(Exception):
    pass


class Repository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = firestore.Client(project=settings.project_id,
            credentials=google.auth.credentials.AnonymousCredentials() if settings.mode == "local" else None)

    def _contended_transaction(self, operation):
        # The SDK preserves aborted transaction IDs between its retries. A fresh
        # transaction releases that lock queue after bounded retry exhaustion.
        # Retry only confirmed aborts; an unknown commit must never be repeated.
        for attempt in range(3):
            try: return operation(self.db.transaction())
            except ValueError as exc:
                if not isinstance(exc.__cause__, Aborted) or attempt == 2: raise
                sleep(uniform(0.05, 0.2) * (attempt + 1))

    def get(self, collection: str, ident: str) -> dict | None:
        doc = self.db.collection(collection).document(ident).get(timeout=5)
        return {"id": doc.id, **doc.to_dict()} if doc.exists else None

    def list(self, collection: str, dataset_id=DATASET_ID) -> list[dict]:
        query = self.db.collection(collection).where(filter=firestore.FieldFilter("dataset_id", "==", dataset_id))
        return [{"id": doc.id, **doc.to_dict()} for doc in query.stream(timeout=10)]

    def create(self, collection: str, ident: str, data: dict):
        self.db.collection(collection).document(ident).create({"schema_version": 1, "created_at": now(), **data}, timeout=10)

    def audit(self, action: str, collection: str, ident: str, actor: str, **fields):
        self.create("audit_events", uuid4().hex, {"dataset_id": DATASET_ID, "action": action,
            "object_collection": collection, "object_id": ident, "actor": actor, "occurred_at": now(), **fields})

    def load_dataset(self) -> Dataset:
        manifest = self.get("datasets", DATASET_ID)
        if not manifest or manifest.get("state") != "READY": raise LookupError("Dataset not seeded; run npm run seed with local emulators running")
        mappings = {}
        for collection, model in [("customers", Customer), ("accounts", Account), ("transactions", Transaction), ("cases", Case)]:
            fields = set(model.model_fields)
            mappings[collection] = {row["id"]: model.model_validate({k: v for k, v in row.items() if k in fields}) for row in self.list(collection)}
        return Dataset(id=DATASET_ID, seed=manifest["seed"], version=manifest["version"],
            reference_labels=manifest["reference_labels"], reference_reasons=manifest["reference_reasons"],
            manifest_hash=manifest["manifest_hash"], **mappings)

    def save_feedback(self, alert_id: str, request, actor: str) -> dict:
        alert_ref = self.db.collection("alerts").document(alert_id)
        tx = self.db.transaction()

        @firestore.transactional
        def write(transaction):
            snapshot = alert_ref.get(transaction=transaction)
            if not snapshot.exists: raise LookupError("Alert not found")
            alert = snapshot.to_dict()
            if alert["dataset_id"] != DATASET_ID: raise Conflict("Dataset mismatch")
            if alert.get("feedback_revision", 0) != request.expected_revision: raise Conflict("Feedback changed; reload before submitting")
            run_id = alert.get("current_run_id")
            if not run_id or alert["status"] != "COMPLETE": raise Conflict("A completed AI triage run is required before operator feedback")
            run_snapshot = self.db.collection("pipeline_runs").document(run_id).get(transaction=transaction)
            run = run_snapshot.to_dict() if run_snapshot.exists else None
            if (not run or run.get("state") != "COMPLETE" or run.get("alert_id") != alert_id
                or run.get("dataset_id") != alert["dataset_id"]): raise Conflict("A valid completed alert run is required")
            self._sealed_chain(transaction, run)
            revision = request.expected_revision + 1
            ident = f"{alert_id}-{revision}"
            event = {"id": ident, "schema_version": 1, "dataset_id": DATASET_ID, "case_id": alert["case_id"],
                "alert_id": alert_id, "triage_run_id": run_id, **request.model_dump(exclude={"expected_revision"}),
                "revision": revision, "actor_uid": actor, "provenance": "HUMAN_OPERATOR", "submitted_at": now()}
            transaction.create(self.db.collection("feedback_events").document(ident), event)
            transaction.update(alert_ref, {"feedback_revision": revision})
            transaction.create(self.db.collection("audit_events").document(uuid4().hex), {
                "dataset_id": DATASET_ID, "action": "FEEDBACK_RECORDED", "object_id": ident,
                "object_collection": "feedback_events", "actor": actor, "occurred_at": now(), "after_hash": content_hash(event)})
            return event
        return write(tx)

    def freeze_analytical_inputs(self, actor):
        from .evolution import analytical_inputs
        import json

        @firestore.transactional
        def read(tx):
            manifest = self.db.collection("datasets").document(DATASET_ID).get(transaction=tx).to_dict()
            if not manifest or manifest.get("state") != "READY": raise Conflict("Dataset is not ready")
            rows = {}
            # ponytail: bounded demo snapshot; use time windows before exceeding
            # 10k records per collection or the conservative document size limit.
            for collection in ("feedback_events", "step_runs", "alerts"):
                query = self.db.collection(collection).where(filter=firestore.FieldFilter("dataset_id", "==", DATASET_ID)).limit(10001)
                rows[collection] = [{"id": doc.id, **doc.to_dict()} for doc in query.stream(transaction=tx)]
                if len(rows[collection]) > 10000: raise Conflict("Analytical input window exceeds demo capacity")
            alerts = {alert["id"]: alert for alert in rows["alerts"]}
            checked = set()
            for event in rows["feedback_events"]:
                alert = alerts.get(event.get("alert_id"))
                if (event.get("provenance") != "HUMAN_OPERATOR" or not alert
                    or event.get("case_id") != alert["case_id"] or not event.get("actor_uid")
                    or event.get("verdict") not in {"TRUE_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE"}
                    or type(event.get("revision")) is not int or event["revision"] < 1):
                    raise Conflict("Invalid feedback provenance")
                run_id = event.get("triage_run_id")
                if (run_id, alert["id"]) in checked: continue
                run = self.db.collection("pipeline_runs").document(run_id or "missing").get(transaction=tx).to_dict()
                if (not run or run.get("state") != "COMPLETE" or run.get("alert_id") != alert["id"]
                    or run.get("dataset_id") != DATASET_ID): raise Conflict("Feedback requires a genuine completed run")
                self._sealed_chain(tx, run)
                checked.add((run_id, alert["id"]))
            for step in rows["step_runs"]:
                if step["state"] == "SUCCEEDED" and step["leg_id"] in {"A2", "A3", "A4", "A5", "EVALUATE"}:
                    if (step.get("execution_provenance") != "REAL_PROVIDER" or step.get("output") is None
                        or not step.get("validation", {}).get("schema_pass")
                        or (step["leg_id"] in {"A2", "A3", "A4"} and not step.get("validation", {}).get("evidence_pass"))):
                        raise Conflict("Succeeded model output has invalid provenance")
            return analytical_inputs(manifest["manifest_hash"], rows["feedback_events"], rows["step_runs"], rows["alerts"])

        body = read(self.db.transaction(read_only=True))
        if len(json.dumps(body, default=str).encode("utf-8")) > 800000: raise Conflict("Analytical snapshot exceeds demo capacity")
        ident = content_hash(body)
        ref = self.db.collection("analytical_snapshots").document(ident)

        @firestore.transactional
        def persist(tx):
            snapshot = ref.get(transaction=tx)
            if snapshot.exists: return {"id": snapshot.id, **snapshot.to_dict()}
            result = {"id": ident, "dataset_id": DATASET_ID, "schema_version": 1,
                "content_hash": ident, "body": body, "created_at": now(), "created_by": actor}
            tx.create(ref, result)
            tx.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "ANALYTICAL_INPUTS_FROZEN", "object_collection": "analytical_snapshots", "object_id": ident,
                "actor": actor, "occurred_at": now(), "after_hash": ident})
            return result
        return self._contended_transaction(persist)

    def evolution_context(self, snapshot_id):
        snapshot = self.get("analytical_snapshots", snapshot_id)
        if not snapshot or snapshot.get("dataset_id") != DATASET_ID: raise LookupError("Analytical snapshot not found")
        body = snapshot["body"]
        if content_hash(body) != snapshot_id or snapshot.get("content_hash") != snapshot_id:
            raise Conflict("Analytical snapshot integrity failed")
        if not body["sample_sizes"]["feedback_events"]: raise Conflict("Genuine analyst feedback is required before A5")
        feedback = []
        rules = {}
        for reference in body["reviewed_alerts"]:
            alert = self.get("alerts", reference["id"])
            if not alert or content_hash({key: alert[key] for key in ("id", "rule_id")}) != reference["hash"]:
                raise Conflict("Frozen alert rule mapping changed")
            rules[alert["id"]] = alert["rule_id"]
        for reference in body["feedback_events"]:
            if reference["id"] not in body["latest_feedback_ids"]: continue
            event = self.get("feedback_events", reference["id"])
            if not event or content_hash(event) != reference["hash"] or event.get("provenance") != "HUMAN_OPERATOR":
                raise Conflict("Frozen feedback changed")
            feedback.append({**event, "rule_id": rules[event["alert_id"]]})
        reviewed_runs = {event["triage_run_id"] for event in feedback}
        outputs = []
        for reference in body["succeeded_steps"]:
            step = self.get("step_runs", reference["id"])
            if not step or content_hash(step) != reference["hash"]: raise Conflict("Frozen succeeded step changed")
            if step["run_id"] in reviewed_runs and step["leg_id"] in {"A2", "A3", "A4"}:
                outputs.append({"id": step["id"], "run_id": step["run_id"], "leg_id": step["leg_id"], "output": step["output"]})
        from .engine import candidate_options
        return {"analytical_inputs": body, "human_feedback": feedback, "sealed_model_suggestions": outputs,
            "candidate_allowlist": candidate_options(), "evidence_ids": body["latest_feedback_ids"],
            "missing_context": [], "protected_signals": []}

    def enqueue_evolution(self, snapshot_id, actor):
        self.evolution_context(snapshot_id)  # Validate immutable inputs before making work.
        from google.api_core.exceptions import AlreadyExists
        bundle_id = self.ensure_baseline()
        ident = stable_id(DATASET_ID, "A5", snapshot_id)
        run = PipelineRun(id=ident, dataset_id=DATASET_ID, kind="EVOLUTION", analytical_snapshot_id=snapshot_id,
            config_bundle_id=bundle_id, actor_uid=actor).model_dump()
        try: self.create("pipeline_runs", ident, run)
        except AlreadyExists: return ident, False
        return ident, True

    def complete_evolution(self, run_id, lease=None):
        from .engine import candidate_options
        run_ref = self.db.collection("pipeline_runs").document(run_id)

        @firestore.transactional
        def complete(tx):
            run = run_ref.get(transaction=tx).to_dict()
            step = self._leg_step(tx, run, "A5") if run else {}
            step_id = step.get("id")
            if (not run or run.get("kind") != "EVOLUTION" or run.get("state") != "RUNNING" or not step
                or step.get("state") != "SUCCEEDED" or step.get("execution_provenance") != "REAL_PROVIDER"
                or step.get("run_id") != run_id or step.get("config_bundle_id") != run["config_bundle_id"]
                or step.get("dataset_id") != DATASET_ID or not step.get("validation", {}).get("schema_pass")
                or not step.get("validation", {}).get("evidence_pass") or not step.get("output")):
                raise Conflict("A validated real A5 result is required")
            self._check_execution_owner(tx, run, lease)
            result = step["output"]
            candidate = next((item for item in candidate_options() if item["id"] == result.get("candidate_id")), None)
            if result["status"] == "SUPPORTED_PROPOSAL":
                if not candidate: raise Conflict("Candidate is not allowlisted")
                version = {"kind": "DETECTOR", "origin": "EVOLUTION", "source_step_id": step_id,
                    "analytical_snapshot_id": run["analytical_snapshot_id"], "body": {"base_detector_version": "detector-v1",
                        "rule_id": "HIGH_VALUE", "candidate": candidate}}
                version_id = content_hash(version)
                recommendation = {"id": run_id, "dataset_id": DATASET_ID, "evolution_run_id": run_id,
                    "state": "PROPOSED", "revision": 0, "config_version_id": version_id, "candidate": candidate,
                    "hypothesis": result["hypothesis"], "support_feedback_ids": result["support_feedback_ids"],
                    "diff": {"component": "DETECTOR", "rule_id": "HIGH_VALUE", "before": "detector-v1", "after": candidate},
                    "activation_allowed": False, "created_at": now()}
                tx.create(self.db.collection("config_versions").document(version_id), {**version, "content_hash": version_id, "created_at": now()})
                tx.create(self.db.collection("recommendations").document(run_id), recommendation)
            tx.update(run_ref, {"state": "COMPLETE", "stage": "A5", "checkpoint_step_id": step_id, "completed_at": now(), "error_code": None})
            tx.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "A5_RECORDED", "object_collection": "pipeline_runs", "object_id": run_id,
                "actor": "local-worker", "occurred_at": now(), "run_id": run_id, "after_hash": content_hash(result)})
        return complete(self.db.transaction())

    def evolution_detail(self, run_id):
        from .usage import run_summary
        run = self.get("pipeline_runs", run_id)
        if not run or run.get("kind") != "EVOLUTION" or run.get("dataset_id") != DATASET_ID: raise LookupError("Evolution run not found")
        result = None
        if run["state"] == "COMPLETE":
            step = self._leg_step(None, run, "A5")
            if (not step or step.get("state") != "SUCCEEDED" or step.get("execution_provenance") != "REAL_PROVIDER"
                or step.get("config_bundle_id") != run["config_bundle_id"] or step.get("dataset_id") != DATASET_ID
                or not step.get("validation", {}).get("schema_pass") or not step.get("validation", {}).get("evidence_pass")):
                raise Conflict("A validated real A5 result is required")
            result = step["output"]
        return {"run": run_summary(run), "analytical_snapshot_id": run["analytical_snapshot_id"],
            "result": result, "recommendation": self.get("recommendations", run_id),
            "optimization_replays": {"prompt": "UNEVALUATED", "skill": "UNEVALUATED", "weight": "UNEVALUATED"},
            "activation_allowed": False}

    def review_recommendation(self, ident, request, actor):
        ref = self.db.collection("recommendations").document(ident)

        @firestore.transactional
        def review(tx):
            stored = ref.get(transaction=tx)
            if not stored.exists: raise LookupError("Recommendation not found")
            before = stored.to_dict()
            if before.get("dataset_id") != DATASET_ID: raise LookupError("Recommendation not found")
            if before.get("revision", 0) != request.expected_revision: raise Conflict("Recommendation changed; reload before reviewing")
            update = {"state": request.state, "review_notes": request.notes, "reviewed_by": actor,
                "reviewed_at": now(), "revision": request.expected_revision + 1, "activation_allowed": False}
            tx.update(ref, update)
            tx.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "RECOMMENDATION_REVIEWED", "object_collection": "recommendations", "object_id": ident,
                "actor": actor, "occurred_at": now(), "before_hash": content_hash(before), "after_hash": content_hash({**before, **update})})
            return {"id": ident, **before, **update}
        return review(self.db.transaction())

    def freeze_candidate(self, request, actor):
        from .engine import candidate_options
        from .evolution import candidate_identity
        ref = self.db.collection("candidate_freezes").document(stable_id(DATASET_ID, "heldout"))
        candidate = next(item for item in candidate_options() if item["id"] == request.candidate_id)

        @firestore.transactional
        def freeze(tx):
            existing = ref.get(transaction=tx)
            manifest = self.db.collection("datasets").document(DATASET_ID).get(transaction=tx).to_dict()
            if not manifest or manifest.get("state") != "READY": raise Conflict("Dataset is not ready")
            identity = candidate_identity(manifest["manifest_hash"], candidate)
            if identity != request.expected_candidate_hash: raise Conflict("Candidate changed; reload before freezing")
            if existing.exists:
                record = existing.to_dict()
                if record["candidate_hash"] != identity: raise Conflict("A detector candidate is already frozen; held-out results cannot guide a new selection")
                return {"id": existing.id, **record}
            run = self.db.collection("pipeline_runs").document(request.evolution_run_id).get(transaction=tx).to_dict()
            step = self._leg_step(tx, run, "A5") if run else {}
            if (not run or run.get("kind") != "EVOLUTION" or run.get("state") != "COMPLETE" or run.get("dataset_id") != DATASET_ID
                or not step or step.get("state") != "SUCCEEDED" or step.get("execution_provenance") != "REAL_PROVIDER"
                or step.get("config_bundle_id") != run["config_bundle_id"] or step.get("dataset_id") != DATASET_ID
                or not step.get("validation", {}).get("schema_pass") or not step.get("validation", {}).get("evidence_pass") or not step.get("output")):
                raise Conflict("Store a genuine validated A5 result before freezing a candidate")
            snapshot = self.db.collection("analytical_snapshots").document(run["analytical_snapshot_id"]).get(transaction=tx).to_dict()
            if (not snapshot or content_hash(snapshot["body"]) != run["analytical_snapshot_id"]
                or snapshot["body"]["dataset_hash"] != manifest["manifest_hash"]): raise Conflict("Frozen source inputs changed")
            supported = (snapshot["body"]["detector_gate"]["status"] == "SUFFICIENT_EVIDENCE"
                and step["output"].get("status") == "SUPPORTED_PROPOSAL" and step["output"].get("candidate_id") == candidate["id"])
            body = {"candidate": candidate, "candidate_hash": identity, "dataset_hash": manifest["manifest_hash"],
                "baseline": "detector-v1", "evolution_run_id": request.evolution_run_id,
                "analytical_snapshot_id": run["analytical_snapshot_id"], "detector_gate": snapshot["body"]["detector_gate"],
                "support_status": "FEEDBACK_SUPPORTED" if supported else "OPERATOR_SELECTED_NOT_FEEDBACK_SUPPORTED",
                "frozen_by": actor, "notes": request.notes, "activation_allowed": False}
            record = {"id": ref.id, "dataset_id": DATASET_ID, **body, "content_hash": content_hash(body), "frozen_at": now()}
            tx.create(ref, record)
            tx.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "DETECTOR_CANDIDATE_FROZEN", "object_collection": "candidate_freezes", "object_id": ref.id,
                "actor": actor, "occurred_at": now(), "after_hash": record["content_hash"]})
            return record
        return self._contended_transaction(freeze)

    def simulate_frozen(self, freeze_id, actor):
        from .engine import simulate
        from .evolution import candidate_identity
        frozen = self.get("candidate_freezes", freeze_id)
        if not frozen or frozen.get("dataset_id") != DATASET_ID: raise LookupError("Frozen candidate not found")
        body = {key: value for key, value in frozen.items() if key not in {"id", "dataset_id", "content_hash", "frozen_at", "schema_version", "created_at"}}
        if content_hash(body) != frozen["content_hash"] or candidate_identity(frozen["dataset_hash"], frozen["candidate"]) != frozen["candidate_hash"]:
            raise Conflict("Frozen candidate integrity failed")
        ref = self.db.collection("simulations").document(freeze_id)

        @firestore.transactional
        def claim(tx):
            snapshot = ref.get(transaction=tx)
            if snapshot.exists: return {"id": snapshot.id, **snapshot.to_dict()}
            tx.create(ref, {"id": freeze_id, "dataset_id": DATASET_ID, "state": "RUNNING", "freeze_id": freeze_id,
                "candidate_hash": frozen["candidate_hash"], "freeze_hash": frozen["content_hash"], "started_at": now(), "actor_uid": actor})
            return None
        existing = self._contended_transaction(claim)
        if existing is not None: return existing
        try:
            data = self.load_dataset()  # Held-out data is opened only after durable freeze and claim.
            if data.manifest_hash != frozen["dataset_hash"]: raise Conflict("Frozen dataset changed")
            metrics = simulate(data, frozen["candidate"], "HOLDOUT")
        except Exception:
            ref.update({"state": "FAILED", "error_code": "SIMULATION_FAILED", "completed_at": now()})
        else:
            batch = self.db.batch()
            batch.update(ref, {"state": "COMPLETE", "metrics": metrics, "completed_at": now(), "error_code": None})
            batch.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "HELDOUT_SIMULATION_RECORDED", "object_collection": "simulations", "object_id": freeze_id,
                "actor": actor, "occurred_at": now(), "after_hash": content_hash(metrics)})
            batch.commit(timeout=10)
        return self.get("simulations", freeze_id)

    def publish(self, cases: list[dict], summary: dict, actor: str) -> str:
        cases_hash = content_hash(cases)
        active = self.publication()
        if active and content_hash(active["public_cases"]) == cases_hash:
            return active["id"]
        ident = uuid4().hex
        payload = {"dataset_id": DATASET_ID, "state": "PUBLISHED", "public_cases": cases,
            "public_summary": summary, "source_provenance": "DETERMINISTIC_ONLY", "published_at": now(), "published_by": actor}
        payload["cases_hash"] = cases_hash
        payload["snapshot_hash"] = content_hash(payload)
        batch = self.db.batch()
        batch.create(self.db.collection("publications").document(ident), payload)
        batch.set(self.db.collection("publications").document("active"), {"publication_id": ident})
        batch.commit(timeout=10)
        return ident

    def publication(self) -> dict | None:
        active = self.get("publications", "active")
        return self.get("publications", active["publication_id"]) if active else None

    def page(self, collection: str, limit=50, cursor: str | None = None, filters=(), order="__name__") -> dict:
        query = self.db.collection(collection)
        for field, value in filters:
            query = query.where(filter=firestore.FieldFilter(field, "==", value))
        query = query.order_by(order, direction=firestore.Query.DESCENDING if order != "__name__" else firestore.Query.ASCENDING)
        if cursor:
            snapshot = self.db.collection(collection).document(cursor).get(timeout=5)
            if not snapshot.exists: raise Conflict("History cursor is no longer available; reload")
            row = snapshot.to_dict()
            if any(row.get(field) != value for field, value in filters) or (order != "__name__" and order not in row):
                raise Conflict("History cursor does not belong to this result set; reload")
            query = query.start_after(snapshot)
        rows = [{"id": doc.id, **doc.to_dict()} for doc in query.limit(limit + 1).stream(timeout=10)]
        return {"items": rows[:limit], "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None}

    def ensure_baseline(self):
        from google.api_core.exceptions import AlreadyExists
        from .engine import WEIGHTS, candidate_options
        components = {}
        versions = [("RISK_POLICY", "RISK_POLICY", {"weights": WEIGHTS}),
            ("CONTEXT", "CONTEXT", {"evidence_version": "evidence-v1", "reference_labels_allowed": False})]
        from .pricing import configured_card
        card = configured_card(self.settings)
        generation_profiles = (self.settings.agent_profiles.frozen_profiles
            if self.settings.local_gemini_enabled or self.settings.mode == "cloud" else None)
        if card is not None:
            versions.append(("RATE_CARD", "RATE_CARD", card.model_dump(mode="json")))
        if self.settings.local_gemini_enabled or self.settings.mode == "cloud":
            from .prompts import CONTEXT_POLICY, LEGS
            versions[1] = ("CONTEXT", "CONTEXT", CONTEXT_POLICY)
            versions.extend((f"PROMPT_{leg}", "PROMPT", {"leg_id": leg, "instructions": spec[3],
                "response_schema": spec[0].model_json_schema(), "input_cap": spec[1], "output_cap": spec[2]}) for leg, spec in LEGS.items())
        for key, kind, body in versions:
            version = {"kind": kind, "origin": "BASELINE", "body": body}
            ident = content_hash(version)
            try: self.create("config_versions", ident, {**version, "content_hash": ident})
            except AlreadyExists: pass
            components[key] = ident
        bundle = {"kind": "BUNDLE", "origin": "BASELINE", "component_ids": components,
            "body": {"detector_version": "detector-v1", "candidate_allowlist": candidate_options()}}
        if self.settings.local_gemini_enabled:
            bundle["body"].update({"model_id": self.settings.active_model_id, "provider": "GEMINI_DEVELOPER_API",
                "attempts_per_leg": 2, "max_daily_attempts": 12})
        elif self.settings.mode == "cloud":
            bundle["body"].update({"model_id": self.settings.model_id, "provider": "GOOGLE_CLOUD",
                "location": self.settings.verified_cloud_location, "attempts_per_leg": 2, "max_daily_attempts": 120})
            if self.settings.deployed_code_fingerprint:
                bundle["body"]["code_fingerprint"] = self.settings.deployed_code_fingerprint
        if generation_profiles is not None:
            bundle["body"]["generation_profiles"] = generation_profiles
            bundle["body"]["leg_models"] = {leg: profile["model_id"] for leg, profile in generation_profiles.items()}
        ident = content_hash(bundle)
        try: self.create("config_versions", ident, {**bundle, "content_hash": ident})
        except AlreadyExists: pass
        return ident

    def claim_batch(self, parent_id, kind="TRIAGE_BATCH"):
        if kind not in {"TRIAGE_BATCH", "EVOLUTION"}: raise ValueError("Unsupported worker run kind")
        ref = self.db.collection("pipeline_runs").document(parent_id)

        @firestore.transactional
        def claim(tx):
            snapshot = ref.get(transaction=tx)
            if not snapshot.exists: return False
            run = snapshot.to_dict()
            if run["kind"] != kind or run["state"] != "QUEUED" or run.get("dispatch_generation", 0): return False
            tx.update(ref, {"state": "RUNNING", "started_at": now()})
            return True
        return self._contended_transaction(claim)

    def prepare_dispatch(self, run_id):
        """Persist task identity before transport; unknown sends reuse that identity."""
        ref = self.db.collection("pipeline_runs").document(run_id)

        @firestore.transactional
        def prepare(tx):
            snapshot = ref.get(transaction=tx)
            run = snapshot.to_dict() if snapshot.exists else None
            if not run or run.get("dataset_id") != DATASET_ID or run.get("kind") not in {"TRIAGE_BATCH", "EVOLUTION"}:
                raise Conflict("DISPATCH_RUN_INVALID")
            if run["state"] not in {"QUEUED", "DISPATCH_FAILED"}: raise Conflict("DISPATCH_RUN_NOT_QUEUED")
            if run.get("dispatch_state") in {"PENDING", "SENT", "UNKNOWN"}:
                return {"run_id": run_id, "generation": run["dispatch_generation"], "task_id": run["dispatch_task_id"]}
            generation = run.get("dispatch_generation", 0) + 1
            task_id = stable_id(DATASET_ID, "dispatch", run_id, generation)
            tx.update(ref, {"state": "QUEUED", "dispatch_generation": generation, "dispatch_task_id": task_id,
                "dispatch_state": "PENDING", "error_code": None})
            tx.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "DISPATCH_PREPARED", "object_collection": "pipeline_runs", "object_id": run_id,
                "actor": run["actor_uid"], "occurred_at": now(), "dispatch_generation": generation})
            return {"run_id": run_id, "generation": generation, "task_id": task_id}
        return self._contended_transaction(prepare)

    def record_dispatch(self, run_id, generation, outcome):
        if outcome not in {"SENT", "UNKNOWN", "FAILED"}: raise ValueError("Invalid dispatch outcome")
        ref = self.db.collection("pipeline_runs").document(run_id)

        @firestore.transactional
        def record(tx):
            snapshot = ref.get(transaction=tx)
            run = snapshot.to_dict() if snapshot.exists else None
            if not run or run.get("dataset_id") != DATASET_ID or run.get("dispatch_generation") != generation:
                raise Conflict("DISPATCH_GENERATION_CHANGED")
            # A delivery or earlier acknowledgement is stronger evidence than a
            # late timeout/failure from CreateTask; do not downgrade it.
            if run.get("dispatch_state") == "SENT": return
            if run.get("dispatch_state") == "FAILED" and outcome == "UNKNOWN": return
            update = {"dispatch_state": outcome}
            if outcome == "UNKNOWN" and run["state"] == "QUEUED": update["error_code"] = "DISPATCH_OUTCOME_UNKNOWN"
            if outcome == "SENT" and run["state"] == "QUEUED": update["error_code"] = None
            if outcome == "SENT" and run["state"] == "DISPATCH_FAILED": update.update(state="QUEUED", error_code=None)
            if outcome == "FAILED" and run["state"] == "QUEUED":
                # A rejected send has not executed any children. Keep active work
                # attached to its alerts so explicit retry reuses this batch.
                update["error_code"] = "DISPATCH_FAILED"
            tx.update(ref, update)
        return self._contended_transaction(record)

    def claim_delivery(self, run_id, generation, owner):
        if type(generation) is not int or generation < 1 or not owner or len(owner) > 128:
            raise ValueError("Invalid delivery claim")
        ref = self.db.collection("pipeline_runs").document(run_id)

        @firestore.transactional
        def claim(tx):
            snapshot = ref.get(transaction=tx)
            run = snapshot.to_dict() if snapshot.exists else None
            if not run or run.get("dataset_id") != DATASET_ID or run.get("kind") not in {"TRIAGE_BATCH", "EVOLUTION"}:
                raise Conflict("WORKER_RUN_INVALID")
            if run.get("dispatch_generation") != generation: return {"status": "STALE", "lease": None}
            if run["state"] in {"COMPLETE", "FAILED", "DISPATCH_FAILED"}: return {"status": "TERMINAL", "lease": None}
            instant = now()
            if run["state"] == "RUNNING":
                if not run.get("lease_expires_at"): raise Conflict("UNLEASED_RUN_ALREADY_ACTIVE")
                if run["lease_expires_at"] > instant: return {"status": "BUSY", "lease": None}
            lease = WorkerLease(run_id=run_id, generation=generation, owner=owner,
                expires_at=instant + timedelta(seconds=300), execution_deadline_at=instant + timedelta(seconds=240))
            tx.update(ref, {"state": "RUNNING", "dispatch_state": "SENT", "lease_owner": owner,
                "lease_expires_at": lease.expires_at, "execution_deadline_at": lease.execution_deadline_at,
                "started_at": run.get("started_at") or instant, "lease_claim_count": run.get("lease_claim_count", 0) + 1})
            tx.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "WORKER_LEASE_CLAIMED", "object_collection": "pipeline_runs", "object_id": run_id,
                "actor": "worker", "occurred_at": instant, "dispatch_generation": generation,
                "claim_number": run.get("lease_claim_count", 0) + 1})
            return {"status": "CLAIMED", "lease": lease}
        return self._contended_transaction(claim)

    def _check_worker_lease(self, tx, lease, *, finishing=False, reserve_seconds=0):
        snapshot = self.db.collection("pipeline_runs").document(lease.run_id).get(transaction=tx)
        run = snapshot.to_dict() if snapshot.exists else {}
        instant = now()
        if (run.get("dataset_id") != DATASET_ID or run.get("state") != "RUNNING"
            or run.get("dispatch_generation") != lease.generation or run.get("lease_owner") != lease.owner
            or not run.get("lease_expires_at") or run["lease_expires_at"] <= instant):
            raise Conflict("WORKER_LEASE_LOST")
        if not finishing and (not run.get("execution_deadline_at") or run["execution_deadline_at"] <= instant + timedelta(seconds=reserve_seconds)):
            raise Conflict("WORKER_EXECUTION_BOUND")
        return run

    def check_worker_lease(self, lease, reserve_seconds=0):
        @firestore.transactional
        def check(tx): return self._check_worker_lease(tx, lease, reserve_seconds=reserve_seconds)
        return check(self.db.transaction(read_only=True))

    def _check_execution_owner(self, tx, run, lease, *, finishing=False):
        root_id = run.get("parent_run_id") or run["id"]
        if lease:
            if root_id != lease.run_id: raise Conflict("WORKER_RUN_LINK_INVALID")
            parent = self._check_worker_lease(tx, lease, finishing=finishing)
            if run["id"] != root_id and (run["id"] not in parent.get("child_run_ids", [])
                or run.get("config_bundle_id") != parent["config_bundle_id"] or run.get("case_id") != parent.get("case_id")):
                raise Conflict("WORKER_RUN_LINK_INVALID")
        else:
            parent = self.db.collection("pipeline_runs").document(root_id).get(transaction=tx).to_dict() if root_id != run["id"] else run
            if self.settings.mode == "cloud" or (parent or {}).get("dispatch_generation", 0): raise Conflict("WORKER_LEASE_REQUIRED")

    def create_worker_step(self, lease, step, *, finishing=False):
        from .usage import TOKEN_FIELDS
        deterministic = (step.leg_id in {"A1", "A0"} and step.state == "SUCCEEDED" and step.output is not None
            and step.execution_provenance == "DETERMINISTIC" and step.validation.get("schema_pass") and step.validation.get("evidence_pass"))
        refused = step.state == "FAILED" and step.output is None and step.execution_provenance == "NOT_SENT"
        if (not (deterministic or refused) or step.model_id is not None or step.usage_status != "NOT_APPLICABLE"
            or step.cost_status != "NOT_APPLICABLE" or (finishing and not refused)
            or any(getattr(step, field) is not None for field in (*TOKEN_FIELDS, "estimated_usd_micros", "provider_usage_raw", "provider_request_id"))):
            raise ValueError("Provider attempts must use reservation and sealing")
        ref = self.db.collection("step_runs").document(step.id)

        @firestore.transactional
        def create(tx):
            run = self.db.collection("pipeline_runs").document(step.run_id).get(transaction=tx).to_dict()
            if (not run or run.get("dataset_id") != DATASET_ID or run.get("state") != "RUNNING"
                or run.get("config_bundle_id") != step.config_bundle_id or run.get("alert_id") != step.alert_id
                or run.get("case_id") != step.case_id): raise Conflict("WORKER_RUN_LINK_INVALID")
            self._check_execution_owner(tx, run, lease, finishing=finishing)
            existing = ref.get(transaction=tx)
            if existing.exists: return {"id": existing.id, **existing.to_dict()}
            row = {**step.model_dump(), "created_at": now(), "schema_version": 1}
            tx.create(ref, row)
            return row
        return self._contended_transaction(create)

    def finish_worker_batch(self, lease):
        ref = self.db.collection("pipeline_runs").document(lease.run_id)

        @firestore.transactional
        def finish(tx):
            parent = self._check_worker_lease(tx, lease, finishing=True)
            if parent["kind"] != "TRIAGE_BATCH": raise Conflict("WORKER_RUN_LINK_INVALID")
            children = [self.db.collection("pipeline_runs").document(ident).get(transaction=tx).to_dict() for ident in parent["child_run_ids"]]
            for child in children:
                if (not child or child.get("dataset_id") != DATASET_ID or child.get("parent_run_id") != lease.run_id
                    or child.get("config_bundle_id") != parent["config_bundle_id"] or child.get("case_id") != parent.get("case_id")
                    or child.get("state") not in {"COMPLETE", "FAILED"}): raise Conflict("CHILD_RUNS_NOT_TERMINAL")
                if child["state"] == "COMPLETE": self._sealed_chain(tx, child)
            errors = [child.get("error_code") or "CHILD_FAILED" for child in children if child["state"] == "FAILED"]
            tx.update(ref, {"state": "FAILED" if errors else "COMPLETE", "completed_at": now(), "error_code": errors[0] if errors else None})
        return self._contended_transaction(finish)

    def worker_update(self, lease, run_id, changes, *, alert_state=None, finishing=False):
        allowed = {"state", "stage", "checkpoint_step_id", "started_at", "completed_at", "error_code"}
        if set(changes) - allowed or alert_state not in {None, "RUNNING", "ERROR"}: raise ValueError("Invalid worker update")
        ref = self.db.collection("pipeline_runs").document(run_id)

        @firestore.transactional
        def update(tx):
            parent = self._check_worker_lease(tx, lease, finishing=finishing)
            snapshot = ref.get(transaction=tx)
            run = snapshot.to_dict() if snapshot.exists else None
            if (not run or run.get("dataset_id") != DATASET_ID
                or (run_id != lease.run_id and (run.get("parent_run_id") != lease.run_id or run_id not in parent.get("child_run_ids", [])
                    or run.get("config_bundle_id") != parent["config_bundle_id"] or run.get("case_id") != parent.get("case_id")))):
                raise Conflict("WORKER_RUN_LINK_INVALID")
            if run.get("state") in {"COMPLETE", "FAILED"}: raise Conflict("WORKER_RUN_TERMINAL")
            if changes.get("state") == "COMPLETE": raise ValueError("Use validated completion, not a generic worker update")
            if run_id == lease.run_id and run["kind"] == "TRIAGE_BATCH" and changes.get("state") == "FAILED":
                children = [self.db.collection("pipeline_runs").document(ident).get(transaction=tx) for ident in run["child_run_ids"]]
                if any(not child.exists or child.to_dict().get("state") not in {"COMPLETE", "FAILED"} for child in children):
                    raise Conflict("CHILD_RUNS_NOT_TERMINAL")
            alert_ref = self.db.collection("alerts").document(run["alert_id"]) if alert_state and run.get("alert_id") else None
            if alert_state:
                alert = alert_ref.get(transaction=tx).to_dict() if alert_ref else None
                if (not alert or alert.get("dataset_id") != DATASET_ID or alert.get("case_id") != run.get("case_id")
                    or alert.get("latest_run_id") != run_id): raise Conflict("WORKER_ALERT_LINK_INVALID")
            tx.update(ref, changes)
            if alert_ref: tx.update(alert_ref, {"status": alert_state})
        return self._contended_transaction(update)

    def recover_started_attempt(self, lease, step_id):
        ref = self.db.collection("step_runs").document(step_id)

        @firestore.transactional
        def recover(tx):
            parent = self._check_worker_lease(tx, lease)
            snapshot = ref.get(transaction=tx)
            if not snapshot.exists: return None
            step = snapshot.to_dict()
            if (step.get("dataset_id") != DATASET_ID
                or step.get("run_id") not in [lease.run_id, *parent.get("child_run_ids", [])]): raise Conflict("WORKER_STEP_LINK_INVALID")
            if step["state"] != "STARTED": return {"id": snapshot.id, **step}
            if (step.get("worker_lease") or {}).get("owner") == lease.owner: raise Conflict("ATTEMPT_STILL_OWNED")
            update = {"state": "UNKNOWN_OUTCOME", "output": None, "execution_provenance": "UNKNOWN", "finished_at": now(), "error_code": "PROVIDER_OUTCOME_UNKNOWN"}
            tx.update(ref, update)
            return {"id": snapshot.id, **step, **update}
        return self._contended_transaction(recover)

    def seal_provider_attempt(self, step, changes):
        from .usage import TOKEN_FIELDS
        if changes.get("state") not in {"SUCCEEDED", "FAILED", "UNKNOWN_OUTCOME"}: raise ValueError("A terminal attempt outcome is required")
        if changes["state"] == "SUCCEEDED" and (changes.get("output") is None
            or changes.get("execution_provenance") != "REAL_PROVIDER" or not changes.get("validation", {}).get("schema_pass")
            or (step.leg_id in {"A2", "A3", "A4", "A5"} and not changes.get("validation", {}).get("evidence_pass"))):
            raise ValueError("Successful provider output requires validation")
        ref = self.db.collection("step_runs").document(step.id)

        @firestore.transactional
        def seal(tx):
            snapshot = ref.get(transaction=tx)
            row = snapshot.to_dict() if snapshot.exists else None
            if (not row or row.get("run_id") != step.run_id or row.get("dataset_id") != step.dataset_id
                or row.get("config_bundle_id") != step.config_bundle_id
                or row.get("worker_lease") != (step.worker_lease.model_dump() if step.worker_lease else None)):
                raise Conflict("ATTEMPT_LINK_INVALID")
            if row["state"] == "STARTED":
                tx.update(ref, changes)
                return True
            if row["state"] == "UNKNOWN_OUTCOME" and not row.get("late_provider_result"):
                usage_keys = {*TOKEN_FIELDS, "usage_status", "provider_usage_raw", "provider_request_id", "provider_service_tier", "cost_status", "estimated_usd_micros", "rate_card_id"}
                measured = {key: value for key, value in changes.items() if key in usage_keys and value is not None}
                tx.update(ref, {**measured, "late_provider_result": {"received_at": now(),
                    "state": changes["state"], "output": changes.get("output"), "validation": changes.get("validation")}})
            return False
        return self._contended_transaction(seal)

    def _leg_step(self, tx, run, leg):
        ident = stable_id(run["id"], leg, 1)
        first = self.db.collection("step_runs").document(ident).get(transaction=tx)
        row = {"id": first.id, **first.to_dict()} if first.exists else {}
        if row and (row.get("id") != ident or row.get("leg_id") != leg or row.get("attempt_number", 1) != 1
            or row.get("retry_of_step_id") is not None or any(row.get(key) != run.get(key if key != "run_id" else "id")
                for key in ("run_id", "dataset_id", "config_bundle_id", "alert_id", "case_id"))):
            raise Conflict("The sealed step linkage is inconsistent")
        if not retry_allowed(row): return row
        second = self.db.collection("step_runs").document(stable_id(run["id"], leg, 2)).get(transaction=tx)
        retry = {"id": second.id, **second.to_dict()} if second.exists else {}
        if (retry.get("retry_of_step_id") != ident or retry.get("attempt_number") != 2
            or any(retry.get(key) != row.get(key) for key in ("run_id", "dataset_id", "config_bundle_id", "alert_id",
                "case_id", "leg_id", "parent_step_ids", "input_hash", "model_id", "prompt_version_id", "context_version_id", "risk_version_id", "rate_card_id"))):
            raise Conflict("The sealed retry chain is incomplete")
        return retry

    def _sealed_chain(self, tx, run):
        if run.get("kind") != "TRIAGE_ALERT": raise Conflict("A completed alert triage is required")
        steps = []
        previous = None
        for leg in ["A1", "A2", "A3", "A4", "A0"]:
            step = self._leg_step(tx, run, leg)
            ident = step.get("id")
            if (step.get("state") != "SUCCEEDED" or step.get("run_id") != run["id"]
                or step.get("config_bundle_id") != run["config_bundle_id"] or step.get("output") is None
                or step.get("dataset_id") != run.get("dataset_id")
                or step.get("alert_id") != run.get("alert_id") or step.get("case_id") != run.get("case_id")
                or step.get("parent_step_ids", []) != ([previous] if previous else [])):
                raise Conflict("The sealed triage chain is incomplete")
            if leg in {"A2", "A3", "A4"} and (step.get("execution_provenance") != "REAL_PROVIDER"
                or not step.get("validation", {}).get("schema_pass") or not step.get("validation", {}).get("evidence_pass")):
                raise Conflict("Validated real provider results are required")
            steps.append(step)
            previous = ident
        return steps

    def complete_alert(self, run_id, lease=None):
        run_ref = self.db.collection("pipeline_runs").document(run_id)

        @firestore.transactional
        def complete(tx):
            snapshot = run_ref.get(transaction=tx)
            run = snapshot.to_dict() if snapshot.exists else None
            if not run or run["state"] != "RUNNING": raise Conflict("Run is not active")
            self._check_execution_owner(tx, run, lease)
            alert_ref = self.db.collection("alerts").document(run["alert_id"])
            alert = alert_ref.get(transaction=tx).to_dict()
            if not alert or alert.get("latest_run_id") != run_id: raise Conflict("A newer investigation owns this alert")
            chain = self._sealed_chain(tx, run)
            tx.update(run_ref, {"state": "COMPLETE", "completed_at": now(), "stage": "A0", "error_code": None})
            tx.update(alert_ref, {"status": "COMPLETE", "current_run_id": run_id,
                "priority": chain[-1]["output"]["priority"]})
        return complete(self.db.transaction())

    def daily_control(self):
        day = now().date().isoformat()
        stored = self.get("usage_daily", day)
        return {key: stored[key] for key in UsageDaily.model_fields} if stored else UsageDaily(
            day_utc=day, credit_verified_until=self.settings.ai_verified_until).model_dump()

    def update_daily_control(self, request, actor):
        day = now().date().isoformat()
        ref = self.db.collection("usage_daily").document(day)

        @firestore.transactional
        def write(tx):
            if now().date().isoformat() != day: raise Conflict("UTC day changed; reload controls")
            snapshot = ref.get(transaction=tx)
            daily = snapshot.to_dict() if snapshot.exists else UsageDaily(day_utc=day).model_dump()
            if daily["revision"] != request.expected_revision: raise Conflict("Controls changed; reload before saving")
            if request.limit < daily["attempts_reserved"]: raise Conflict("Limit cannot be below reserved attempts")
            if request.live_enabled and not self.settings.ai_authorized(): raise Conflict("Unexpired verified cloud credits or local Gemini free-tier access are required")
            if self.settings.local_gemini_enabled and request.limit > 12: raise Conflict("Local Gemini testing is limited to 12 attempts per UTC day")
            updated = UsageDaily.model_validate({**daily, "limit": request.limit, "live_enabled": request.live_enabled,
                "credit_verified_until": self.settings.ai_verified_until, "revision": daily["revision"] + 1}).model_dump()
            tx.set(ref, updated)
            tx.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "DAILY_CONTROL_UPDATED", "object_collection": "usage_daily", "object_id": day,
                "actor": actor, "occurred_at": now(), "before_hash": content_hash(daily), "after_hash": content_hash(updated)})
            return updated
        return write(self.db.transaction())

    def usage_steps(self, run_id=None):
        query = self.db.collection("step_runs").where(filter=firestore.FieldFilter("run_id" if run_id else "dataset_id", "==", run_id or DATASET_ID))
        # ponytail: bounded demo scan; use explicit time windows if this grows beyond 10k steps.
        rows = [{"id": doc.id, **doc.to_dict()} for doc in query.limit(10001).stream(timeout=10)]
        if len(rows) > 10000: raise Conflict("Usage window exceeds demo capacity")
        if any(row.get("dataset_id") != DATASET_ID for row in rows): raise Conflict("Attempt dataset linkage is inconsistent")
        return rows

    def reserve_model_attempt(self, step: StepRun) -> bool:
        """Atomically claim an attempt and ledger row; False means never send it again.

        No provider code runs here. The future gateway must call transport only after
        True, outside this transaction, and seal the STARTED row with its real outcome.
        """
        if (step.state != "STARTED" or step.output is not None or step.retry_delay_seconds is not None
            or step.leg_id not in {"A2", "A3", "A4", "A5", "EVALUATE"}
            or step.dataset_id != DATASET_ID or not self.settings.is_model_authorized(step.model_id, step.leg_id)
            or step.usage_status != "UNKNOWN" or step.cost_status != "UNKNOWN"
            or step.id != stable_id(step.run_id, step.leg_id, step.attempt_number)
            or any(getattr(step, key) is not None for key in ("prompt_tokens", "cached_prompt_tokens", "candidate_tokens",
                "thought_tokens", "tool_prompt_tokens", "total_tokens", "estimated_usd_micros", "provider_usage_raw", "provider_request_id", "provider_service_tier"))):
            raise ValueError("Reservation requires a fresh, unmeasured provider attempt")
        step_ref = self.db.collection("step_runs").document(step.id)
        run_ref = self.db.collection("pipeline_runs").document(step.run_id)

        @firestore.transactional
        def reserve(tx):
            instant = now()
            day = instant.date().isoformat()
            daily_ref = self.db.collection("usage_daily").document(day)
            # Read the shared write target first so competing attempts contend in
            # one consistent order before locking their distinct step records.
            daily_snapshot = daily_ref.get(transaction=tx)
            existing = step_ref.get(transaction=tx)
            if existing.exists: return False
            run_snapshot = run_ref.get(transaction=tx)
            if not self.settings.ai_authorized(): raise Conflict("AI_NOT_CONNECTED")
            if not run_snapshot.exists: raise Conflict("RUN_NOT_ACTIVE")
            run = run_snapshot.to_dict()
            if step.leg_id == "EVALUATE" and run["kind"] != "EVALUATION": raise Conflict("RUN_NOT_ACTIVE")
            if run["state"] != "RUNNING" or run["dataset_id"] != step.dataset_id or run["config_bundle_id"] != step.config_bundle_id:
                raise Conflict("RUN_NOT_ACTIVE")
            if step.alert_id != run.get("alert_id") or step.case_id != run.get("case_id"): raise Conflict("RUN_NOT_ACTIVE")
            bundle = self.db.collection("config_versions").document(step.config_bundle_id).get(transaction=tx).to_dict() or {}
            if self.settings.mode == "cloud" and (not self.settings.deployed_code_fingerprint
                or bundle.get("body", {}).get("code_fingerprint") != self.settings.deployed_code_fingerprint):
                raise Conflict("CONFIG_SOURCE_MISMATCH")
            if step.leg_id in {"A2", "A3", "A4", "A5"}:
                from .agent_profiles import frozen_profile
                try: profile = frozen_profile(bundle, step.leg_id, self.settings.active_model_id)
                except ValueError: raise Conflict("CONFIG_GENERATION_MISMATCH") from None
                if profile.model_id != step.model_id: raise Conflict("CONFIG_MODEL_MISMATCH")
                if "generation_profiles" in bundle.get("body", {}):
                    request = step.input_snapshot
                    config = request.get("generation_config", {})
                    expected_config = {"response_mime_type": "application/json", "max_output_tokens": profile.max_output_tokens,
                        "thinking_config": {"thinking_level": profile.thinking_level}, "automatic_function_calling": {"disable": True}}
                    if profile.temperature is not None: expected_config["temperature"] = profile.temperature
                    if bundle.get("component_ids", {}).get("RATE_CARD"): expected_config["service_tier"] = "standard"
                    if (request.get("model_id") != profile.model_id or step.input_hash != content_hash(request)
                        or config != expected_config):
                        raise Conflict("CONFIG_GENERATION_MISMATCH")
            if step.rate_card_id != bundle.get("component_ids", {}).get("RATE_CARD"):
                raise Conflict("CONFIG_RATE_CARD_MISMATCH")
            daily = UsageDaily.model_validate(daily_snapshot.to_dict()) if daily_snapshot.exists else UsageDaily(day_utc=day)
            if not daily.live_enabled: raise Conflict("LIVE_AI_DISABLED")
            if daily.credit_verified_until is None or daily.credit_verified_until <= instant: raise Conflict("CREDIT_VERIFICATION_EXPIRED")
            if now().date().isoformat() != day: raise Conflict("UTC_DAY_CHANGED")
            if daily.attempts_reserved != len(set(daily.reserved_attempt_ids)) or step.id in daily.reserved_attempt_ids:
                raise Conflict("RESERVATION_INCONSISTENT")
            effective_limit = min(daily.limit, 12) if self.settings.local_gemini_enabled else daily.limit
            if daily.attempts_reserved >= effective_limit: raise Conflict("CAP_REACHED")
            if step.worker_lease:
                if step.worker_lease.run_id != (run.get("parent_run_id") or run["id"]): raise Conflict("WORKER_RUN_LINK_INVALID")
                self._check_worker_lease(tx, step.worker_lease, reserve_seconds=35)
            elif self.settings.mode == "cloud": raise Conflict("WORKER_LEASE_REQUIRED")
            if step.attempt_number == 1:
                if step.retry_of_step_id is not None or step.retry_delay_seconds is not None: raise Conflict("RETRY_NOT_ALLOWED")
            else:
                first_id = stable_id(step.run_id, step.leg_id, 1)
                first = self.db.collection("step_runs").document(first_id).get(transaction=tx).to_dict() or {}
                bundle = self.db.collection("config_versions").document(step.config_bundle_id).get(transaction=tx).to_dict() or {}
                if bundle.get("body", {}).get("attempts_per_leg", 1) != 2: raise Conflict("RETRY_NOT_ALLOWED")
                if (step.attempt_number != 2 or step.retry_of_step_id != first_id or not retry_allowed(first)
                    or any(first.get(key) != getattr(step, key) for key in ("run_id", "dataset_id", "config_bundle_id", "alert_id",
                        "case_id", "leg_id", "parent_step_ids", "input_hash", "input_snapshot", "model_id",
                        "prompt_version_id", "context_version_id", "risk_version_id", "rate_card_id"))): raise Conflict("RETRY_NOT_ALLOWED")
                if not first.get("finished_at") or instant < first["finished_at"] + timedelta(seconds=first["retry_delay_seconds"]):
                    raise Conflict("RETRY_TOO_EARLY")
            daily.attempts_reserved += 1
            daily.reserved_attempt_ids.append(step.id)
            daily.revision += 1
            tx.set(daily_ref, daily.model_dump())
            tx.create(step_ref, {**step.model_dump(), "execution_provenance": "UNKNOWN", "started_at": instant, "created_at": instant, "schema_version": 1})
            return True
        return self._contended_transaction(reserve)

    def run_detail(self, run_id):
        from .usage import attempt_summary, run_summary, summarize
        parent = self.get("pipeline_runs", run_id)
        if not parent or parent["dataset_id"] != DATASET_ID: raise LookupError("Run not found")
        children = [self.get("pipeline_runs", ident) for ident in parent.get("child_run_ids", [])]
        if any(not child or child.get("dataset_id") != DATASET_ID or child.get("parent_run_id") != parent["id"] for child in children):
            raise Conflict("Child run linkage is inconsistent")
        steps = [step for run in (children or [parent]) if run for step in self.usage_steps(run["id"])]
        return {**run_summary(parent), "children": [run_summary(run) for run in children if run],
            "attempts": [attempt_summary(step) for step in sorted(steps, key=lambda s: (s["run_id"], s["started_at"], s["attempt_number"]))],
            "usage": summarize(steps)}

    def enqueue_triage(self, alert_ids, actor):
        if len(set(alert_ids)) != len(alert_ids): raise ValueError("Duplicate alert IDs are not allowed")
        alerts = [self.get("alerts", ident) for ident in alert_ids]
        if any(not alert or alert["dataset_id"] != DATASET_ID for alert in alerts): raise LookupError("Alert not found")
        case_id = alerts[0]["case_id"]
        if any(alert["case_id"] != case_id for alert in alerts): raise ValueError("Choose alerts from one case")
        all_ids = {alert["id"] for alert in self.list("alerts") if alert["case_id"] == case_id}
        if set(alert_ids) != all_ids: raise ValueError("Send all alerts on the selected case")
        alert_ids = sorted(alert_ids)
        bundle_id = self.ensure_baseline()
        parent_id = uuid4().hex
        children = {ident: uuid4().hex for ident in alert_ids}
        refs = [self.db.collection("alerts").document(ident) for ident in alert_ids]

        @firestore.transactional
        def enqueue(tx):
            snapshots = [ref.get(transaction=tx) for ref in refs]
            latest = {snapshot.to_dict().get("latest_parent_run_id") for snapshot in snapshots}
            parents = [self.db.collection("pipeline_runs").document(ident).get(transaction=tx) for ident in latest if ident]
            for parent in parents:
                if parent.exists and parent.to_dict()["state"] in {"QUEUED", "RUNNING"}: return parent.id, False
            parent = PipelineRun(id=parent_id, dataset_id=DATASET_ID, kind="TRIAGE_BATCH", case_id=case_id,
                config_bundle_id=bundle_id, actor_uid=actor, child_run_ids=list(children.values())).model_dump()
            tx.create(self.db.collection("pipeline_runs").document(parent_id), {**parent, "created_at": now()})
            for ref, alert_id in zip(refs, alert_ids):
                child = PipelineRun(id=children[alert_id], dataset_id=DATASET_ID, kind="TRIAGE_ALERT", parent_run_id=parent_id,
                    alert_id=alert_id, case_id=case_id, config_bundle_id=bundle_id, actor_uid=actor).model_dump()
                tx.create(self.db.collection("pipeline_runs").document(child["id"]), {**child, "created_at": now()})
                tx.update(ref, {"latest_run_id": child["id"], "latest_parent_run_id": parent_id,
                    "status": "PENDING", "current_run_id": None, "priority": None})
            tx.create(self.db.collection("audit_events").document(uuid4().hex), {"dataset_id": DATASET_ID,
                "action": "QUEUED", "object_collection": "pipeline_runs", "object_id": parent_id,
                "run_id": parent_id, "actor": actor, "occurred_at": now()})
            return parent_id, True
        return self._contended_transaction(enqueue)

    def alert_detail(self, alert_id):
        alert = self.get("alerts", alert_id)
        if not alert or alert["dataset_id"] != DATASET_ID: raise LookupError("Alert not found")
        latest = self.get("pipeline_runs", alert["latest_run_id"]) if alert.get("latest_run_id") else None
        if alert.get("latest_run_id") and (not latest or latest.get("dataset_id") != DATASET_ID or latest.get("alert_id") != alert_id):
            raise Conflict("Latest run linkage is inconsistent")
        from .usage import run_summary
        # Only validated output from successful private steps can become a brief.
        output = {}
        if alert.get("current_run_id"):
            @firestore.transactional
            def read_output(tx):
                snapshot = self.db.collection("pipeline_runs").document(alert["current_run_id"]).get(transaction=tx)
                run = snapshot.to_dict() if snapshot.exists else None
                if not run or run.get("state") != "COMPLETE" or run.get("alert_id") != alert_id:
                    raise Conflict("A completed alert triage is required")
                return {step["leg_id"]: step["output"] for step in self._sealed_chain(tx, run)}
            output = read_output(self.db.transaction(read_only=True))
        return {"alert": alert, "latest_run": run_summary(latest) if latest else None, "outputs": output}
