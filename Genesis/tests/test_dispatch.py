"""Task transport doubles stay in memory; no cloud clients or AI output are created."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import AlreadyExists, InvalidArgument, PermissionDenied

from backend.config import Settings
from backend.dispatch import dispatch_configured, dispatch_run
from backend.repository import Conflict


def test_dispatch_is_gated_named_authenticated_and_not_automatically_retried(monkeypatch):
    settings = Settings("cloud", "unit-project", None, None, True, "unused", frozenset(),
        credits_verified=True, credit_verified_until=datetime.now(timezone.utc) + timedelta(minutes=5),
        worker_audience="https://unit-worker.run.app", task_invoker_email="tasks@unit-project.iam.gserviceaccount.com",
        cloud_tasks_enabled=True, task_queue_path="projects/unit-project/locations/test-region/queues/unit-queue",
        verified_cloud_model_id="unused", verified_cloud_location="global")
    assert dispatch_configured(settings)
    events, calls = [], []
    run = {"state": "QUEUED", "dispatch_state": "PENDING"}
    prepared = {"run_id": "a" * 24, "generation": 1, "task_id": "f" * 24}
    outcome = None

    def prepare(_ident):
        events.append("prepare")
        return prepared

    def record(_ident, generation, state):
        assert generation == 1
        events.append(state)
        run["dispatch_state"] = state

    class Client:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def create_task(self, **kwargs):
            events.append("send")
            calls.append(kwargs)
            if outcome: raise outcome

    monkeypatch.setattr("backend.dispatch.tasks_v2.CloudTasksClient", Client)
    repo = SimpleNamespace(settings=settings, get=lambda *_args: run, prepare_dispatch=prepare, record_dispatch=record)
    for change in [{"cloud_tasks_enabled": False}, {"credits_verified": False}, {"live_ai": False}, {"mode": "local"},
        {"verified_cloud_model_id": ""}, {"model_id": "unverified-replacement"}, {"verified_cloud_location": ""},
        {"credit_verified_until": datetime.now(timezone.utc) - timedelta(seconds=1)},
        {"task_queue_path": "projects/other-project/locations/test-region/queues/unit-queue"}]:
        repo.settings = replace(settings, **change)
        assert not dispatch_configured(repo.settings)
        with pytest.raises(Conflict, match="CLOUD_DISPATCH_NOT_AUTHORIZED"): dispatch_run(repo, prepared["run_id"])
        assert not events
    repo.settings = settings
    outcome = TimeoutError("unknown create result")
    dispatch_run(repo, prepared["run_id"])
    assert events == ["prepare", "send", "UNKNOWN"] and len(calls) == 1
    first_task = calls[0]["task"]
    assert calls[0]["retry"] is None and calls[0]["timeout"] == 10
    assert first_task.name == settings.task_queue_path + "/tasks/" + prepared["task_id"]
    assert first_task.dispatch_deadline.total_seconds() == 300
    assert first_task.http_request.url == settings.worker_audience + "/internal/jobs"
    assert first_task.http_request.oidc_token.audience == settings.worker_audience
    assert first_task.http_request.oidc_token.service_account_email == settings.task_invoker_email
    assert json.loads(first_task.http_request.body) == {"run_id": prepared["run_id"], "generation": 1}
    outcome = AlreadyExists("exact task exists or is tombstoned")
    dispatch_run(repo, prepared["run_id"])
    assert calls[1]["task"] == first_task and run["dispatch_state"] == "SENT"
    dispatch_run(repo, prepared["run_id"])
    assert len(calls) == 2  # Known sends do not repeat even CreateTask.
    for failure in [InvalidArgument("bad configuration"), PermissionDenied("missing IAM")]:
        run["dispatch_state"] = "PENDING"
        outcome = failure
        dispatch_run(repo, prepared["run_id"])
        assert run["dispatch_state"] == "FAILED"
    run["state"] = "RUNNING"
    before = len(calls)
    dispatch_run(repo, prepared["run_id"])
    assert len(calls) == before
