"""Firestore is the only mutable application store; no in-memory verdict registry."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import google.auth.credentials
from google.cloud import firestore

from .config import Settings
from .dataset import DATASET_ID, content_hash
from .models import Account, Case, Customer, Dataset, Transaction


def now():
    return datetime.now(timezone.utc)


class Conflict(Exception):
    pass


class Repository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = firestore.Client(project=settings.project_id,
            credentials=google.auth.credentials.AnonymousCredentials() if settings.mode == "local" else None)

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

    def publish(self, cases: list[dict], summary: dict, actor: str) -> str:
        ident = uuid4().hex
        payload = {"dataset_id": DATASET_ID, "state": "PUBLISHED", "public_cases": cases,
            "public_summary": summary, "source_provenance": "DETERMINISTIC_ONLY", "published_at": now(), "published_by": actor}
        payload["snapshot_hash"] = content_hash(payload)
        batch = self.db.batch()
        batch.create(self.db.collection("publications").document(ident), payload)
        batch.set(self.db.collection("publications").document("active"), {"publication_id": ident})
        batch.commit(timeout=10)
        return ident

    def publication(self) -> dict | None:
        active = self.get("publications", "active")
        return self.get("publications", active["publication_id"]) if active else None
