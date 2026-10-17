"""Persist task identity before one explicit Cloud Tasks send; no SDK retries."""
import json
import re

from google.api_core.exceptions import AlreadyExists, InvalidArgument, NotFound, PermissionDenied, Unauthenticated
from google.cloud import tasks_v2
from google.protobuf.duration_pb2 import Duration

from .repository import Conflict


def dispatch_configured(settings):
    return (settings.cloud_tasks_enabled and settings.worker_configured() and settings.cloud_model_valid()
        and bool(re.fullmatch(r"projects/" + re.escape(settings.project_id)
            + r"/locations/[a-z][a-z0-9-]{0,62}/queues/[A-Za-z0-9_-]{1,100}", settings.task_queue_path)))


def dispatch_run(repo, run_id):
    settings = repo.settings
    if not dispatch_configured(settings): raise Conflict("CLOUD_DISPATCH_NOT_AUTHORIZED")
    run = repo.get("pipeline_runs", run_id)
    if not run: raise LookupError("Run not found")
    if run["state"] not in {"QUEUED", "DISPATCH_FAILED"}: return
    if run.get("dispatch_state") == "SENT": return
    try: prepared = repo.prepare_dispatch(run_id)
    except Conflict as exc:
        if str(exc) == "DISPATCH_RUN_NOT_QUEUED" and repo.get("pipeline_runs", run_id)["state"] not in {"QUEUED", "DISPATCH_FAILED"}:
            return  # A concurrent delivery already owns the run.
        raise
    task = tasks_v2.Task(name=settings.task_queue_path + "/tasks/" + prepared["task_id"],
        dispatch_deadline=Duration(seconds=300), http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST, url=settings.worker_audience.rstrip("/") + "/internal/jobs",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"run_id": run_id, "generation": prepared["generation"]}, separators=(",", ":")).encode(),
            oidc_token=tasks_v2.OidcToken(service_account_email=settings.task_invoker_email, audience=settings.worker_audience)))
    # Recheck expiry immediately before constructing an authenticated client.
    if not dispatch_configured(settings):
        repo.record_dispatch(run_id, prepared["generation"], "FAILED")
        raise Conflict("CLOUD_DISPATCH_NOT_AUTHORIZED")
    try:
        with tasks_v2.CloudTasksClient() as client:
            client.create_task(parent=settings.task_queue_path, task=task, retry=None, timeout=10)
        outcome = "SENT"
    except AlreadyExists:
        # The exact persisted identity exists (or is tombstoned). Never invent
        # another ID to bypass deduplication after an unknown CreateTask result.
        outcome = "SENT"
    except (InvalidArgument, NotFound, PermissionDenied, Unauthenticated):
        outcome = "FAILED"
    except Exception:
        outcome = "UNKNOWN"
    repo.record_dispatch(run_id, prepared["generation"], outcome)
