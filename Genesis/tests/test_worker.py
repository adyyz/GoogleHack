"""Worker boundary tests use signed local JWTs, never cloud tokens or provider output."""
import json
import subprocess
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from google.auth import crypt, jwt

from backend.config import Settings
from backend.models import WorkerLease
from backend.worker import create_app, execute_delivery


def test_worker_requires_verified_task_identity_before_claiming(monkeypatch):
    settings = Settings("cloud", "unit-project", None, None, False, "unused", frozenset(),
        worker_audience="https://unit-worker.run.app", task_invoker_email="tasks@unit-project.iam.gserviceaccount.com")
    assert settings.worker_configured()
    for change in [{"mode": "local"}, {"worker_audience": "https://user:pass@unit-worker.run.app"},
        {"worker_audience": "https://unit-worker.run.app/?secret=x"}, {"worker_audience": "http://localhost"},
        {"task_invoker_email": "tasks@other-project.iam.gserviceaccount.com"}]:
        assert not replace(settings, **change).worker_configured()
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    signer = crypt.RSASigner.from_string(pem, key_id="unit-only")
    certs = SimpleNamespace(status=200, data=json.dumps({"unit-only": public.decode()}).encode())
    monkeypatch.setattr("backend.worker.GoogleRequest", lambda: lambda *_args, **_kwargs: certs)
    seen = []
    from backend.bulk_dataset import ID
    record = {"dataset_id": ID, "kind": "EVOLUTION"}
    repo = SimpleNamespace(settings=settings, get=lambda *_args: record, claim_delivery=lambda *args: (seen.append(args) or {"status": "TERMINAL", "lease": None}))
    monkeypatch.setattr("backend.bulk_analytics.AnalyticsRepository", lambda _settings: repo)
    monkeypatch.setattr("backend.worker.Repository", lambda _settings: repo)
    client = TestClient(create_app(settings))
    body = {"run_id": "a" * 24, "generation": 1}
    issued = int(datetime.now(timezone.utc).timestamp())
    claims = {"iss": "https://accounts.google.com", "aud": settings.worker_audience, "sub": "unit-subject",
        "email": settings.task_invoker_email, "email_verified": True, "iat": issued, "exp": issued + 300}

    def headers(changes=None):
        token = jwt.encode(signer, {**claims, **(changes or {})}).decode()
        return {"Authorization": "Bearer " + token}

    assert client.post("/internal/jobs", json=body, headers={"X-CloudTasks-TaskName": "forged"}).status_code == 401
    assert client.post("/internal/jobs", json=body, headers={"Authorization": "Bearer unsigned"}).status_code == 401
    head, payload, signature = headers()["Authorization"].split(".")
    forged = head + "." + payload + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
    assert client.post("/internal/jobs", json=body, headers={"Authorization": forged}).status_code == 401
    for change in [{"aud": "https://other.run.app"}, {"iss": "https://forged.invalid"}, {"exp": issued - 60}]:
        assert client.post("/internal/jobs", json=body, headers=headers(change)).status_code == 401
    for change in [{"email": "wrong@unit-project.iam.gserviceaccount.com"}, {"email_verified": False}]:
        assert client.post("/internal/jobs", json=body, headers=headers(change)).status_code == 403
    assert not seen
    for invalid in [{**body, "generation": True}, {**body, "generation": "1"}, {**body, "extra": "x"},
        {**body, "run_id": "../private"}]:
        assert client.post("/internal/jobs", json=invalid, headers=headers()).status_code == 422
    assert not seen
    response = client.post("/internal/jobs", json=body, headers=headers())
    assert response.status_code == 200 and response.json() == {"status": "TERMINAL"}
    assert response.headers["cache-control"] == "no-store" and len(seen) == 1
    record["dataset_id"] = "synthetic-v1-20261015"
    assert client.post("/internal/jobs", json=body, headers=headers()).status_code == 404
    assert len(seen) == 1
    record["dataset_id"] = ID
    repo.claim_delivery = lambda *_args: {"status": "BUSY", "lease": None}
    assert client.post("/internal/jobs", json=body, headers=headers()).status_code == 503
    assert client.get("/docs").status_code == 404 and client.get("/api/demo/cases").status_code == 404
    closed = TestClient(create_app(replace(settings, mode="local")))
    assert closed.post("/internal/jobs", json=body, headers=headers()).status_code == 503


def test_worker_process_cutoff_preserves_attempts_and_sanitizes_results(monkeypatch):
    instant = datetime.now(timezone.utc)
    lease = WorkerLease(run_id="a" * 24, generation=1, owner="unit-worker", expires_at=instant + timedelta(seconds=300),
        execution_deadline_at=instant + timedelta(seconds=240))
    repo = SimpleNamespace(get=lambda *_args: {"state": "FAILED", "output": "private narrative"})
    calls = []

    def timeout(args, **kwargs):
        calls.append((args, kwargs))
        raise subprocess.TimeoutExpired(args, kwargs["timeout"], output="sensitive output")

    monkeypatch.setattr("backend.worker.subprocess.run", timeout)
    with pytest.raises(HTTPException) as error: execute_delivery(repo, lease)
    assert error.value.status_code == 503 and error.value.detail == "WORKER_INTERRUPTED"
    args, options = calls[0]
    assert args[-3:] == ["-m", "backend.jobs", "--delivery"] and lease.owner not in args
    assert 230 < options["timeout"] <= 240 and json.loads(options["input"])["owner"] == lease.owner
    assert options["stdout"] == subprocess.DEVNULL and options["stderr"] == subprocess.DEVNULL
    monkeypatch.setattr("backend.worker.subprocess.run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0))
    assert execute_delivery(repo, lease) == {"status": "TERMINAL", "state": "FAILED"}
    repo.get = lambda *_args: {"state": "RUNNING"}
    with pytest.raises(HTTPException, match="WORKER_NOT_TERMINAL"): execute_delivery(repo, lease)
    expired = lease.model_copy(update={"execution_deadline_at": instant - timedelta(seconds=1)})
    with pytest.raises(HTTPException, match="WORKER_EXECUTION_BOUND"): execute_delivery(repo, expired)
