"""Publication gates and immutable-source checks without ADC or cloud access."""
from dataclasses import replace
from datetime import timedelta
import json
from types import SimpleNamespace

import pytest

from backend.config import Settings
from backend.publisher import MANIFEST, PROJECT, _check_records, main, publication_plan, validate_approval
from backend.repository import Conflict, now


def approved():
    settings = Settings(mode="cloud", project_id=PROJECT, firestore_host=None, auth_host=None,
        live_ai=False, model_id="verified-model", operator_uids=frozenset({"real-operator"}),
        admin_uids=frozenset({"real-operator"}), credits_verified=True,
        credit_verified_until=now() + timedelta(minutes=10), verified_cloud_model_id="verified-model",
        verified_cloud_location="global", deployed_code_fingerprint="a" * 64)
    approval = {"status": "APPROVED_FOR_SOURCE_PUBLICATION", "source_publication_authorized": True,
        "project_id": PROJECT, "database": "(default)", "manifest_hash": MANIFEST,
        "publisher_identity": "genesis-demo-web@genesis-aicb.iam.gserviceaccount.com",
        "approved_service_coverage": ["firestore"],
        "credit_verification_expires_at": settings.credit_verified_until.isoformat(),
        "operator_uids": ["real-operator"], "admin_uids": ["real-operator"], "code_fingerprint": "a" * 64}
    return settings, approval


def test_default_publication_plan_is_offline_and_requires_exact_approved_target(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs): raise AssertionError("Dry run must not construct Settings, ADC or a client")
    monkeypatch.setattr("backend.publisher.Repository", forbidden)
    monkeypatch.setattr(Settings, "load", forbidden)
    result = main(["--project", PROJECT, "--approved-manifest", MANIFEST])
    assert result["status"] == "OFFLINE_DRY_RUN" and not result["cloud_connected"] and not result["writes_performed"]
    assert result["public_case_count"] == 12 and result["source_counts"]["cases"] == 112
    assert json.loads(capsys.readouterr().out) == result
    for project, manifest, database in [("demo-aml-insight", MANIFEST, "(default)"),
        (PROJECT, "wrong-manifest", "(default)"), (PROJECT, MANIFEST, "other")]:
        with pytest.raises(ValueError): publication_plan(project, manifest, database)
    with pytest.raises(Conflict, match="PUBLICATION_REVIEW_REQUIRED"):
        main(["--project", PROJECT, "--approved-manifest", MANIFEST, "--apply"])


def test_apply_requires_reviewed_funding_identity_uids_and_all_execution_disabled():
    settings, approval = approved()
    assert validate_approval(settings, approval) == approval["publisher_identity"]
    for changes in [{"live_ai": True}, {"local_gemini_enabled": True}, {"cloud_tasks_enabled": True},
        {"credits_verified": False}, {"credit_verified_until": now() - timedelta(seconds=1)},
        {"mode": "local"}, {"project_id": "other-project"}, {"firestore_host": "127.0.0.1:8081"},
        {"auth_host": "127.0.0.1:9099"}, {"operator_uids": frozenset({"operator-demo"})},
        {"admin_uids": frozenset()}, {"verified_cloud_model_id": "different-model"}, {"verified_cloud_location": ""},
        {"deployed_code_fingerprint": ""}, {"deployed_code_fingerprint": "b" * 64}]:
        with pytest.raises(Conflict): validate_approval(replace(settings, **changes), approval)
    for changes in [{"status": "PREPARATION_ONLY"}, {"source_publication_authorized": False},
        {"project_id": "other-project"}, {"database": "other"}, {"manifest_hash": "wrong-manifest"},
        {"approved_service_coverage": []}, {"approved_service_coverage": "firestore"},
        {"publisher_identity": "publisher@other-project.iam.gserviceaccount.com"},
        {"publisher_identity": "somebody@example.com"}, {"operator_uids": ["different"]},
        {"credit_verification_expires_at": "not-a-date"}, {"credit_verification_expires_at": "2026-10-17T12:00:00"}]:
        with pytest.raises(Conflict): validate_approval(settings, {**approval, **changes})


def test_apply_checks_adc_identity_and_default_database_before_preparing_source(monkeypatch, tmp_path):
    settings, approval = approved()
    path = tmp_path / "reviewed-authorization.json"
    path.write_text(json.dumps(approval))
    monkeypatch.setattr(Settings, "load", lambda: settings)
    prepared = []
    monkeypatch.setattr("backend.publisher._prepare_source", lambda *_args: prepared.append(True))
    for project, database, identity in [(PROJECT, "(default)", "unapproved@example.com"),
        (PROJECT, "other", approval["publisher_identity"]), ("other-project", "(default)", approval["publisher_identity"])]:
        repo = SimpleNamespace(db=SimpleNamespace(project=project, _database=database,
            _credentials=SimpleNamespace(service_account_email=identity)))
        monkeypatch.setattr("backend.publisher.Repository", lambda _settings: repo)
        with pytest.raises(Conflict, match="PUBLICATION_IDENTITY_MISMATCH"):
            main(["--project", PROJECT, "--approved-manifest", MANIFEST, "--apply", "--approval-file", str(path)])
    assert not prepared


def test_source_comparison_refuses_changes_and_preserves_mutable_alert_fields():
    record = {"id": "customer", "dataset_id": "dataset", "name": "Fictional original"}
    repo = SimpleNamespace(list=lambda _collection: [{**record, "created_at": now(), "schema_version": 1}])
    assert _check_records(repo, {"customers": {"customer": record}}, complete=True) == []
    repo.list = lambda _collection: [{**record, "name": "changed"}]
    with pytest.raises(Conflict, match="EXISTING_SOURCE_MISMATCH"):
        _check_records(repo, {"customers": {"customer": record}})
    repo.list = lambda _collection: [{**record, "private_injected_output": "not permitted"}]
    with pytest.raises(Conflict, match="EXISTING_SOURCE_MISMATCH"):
        _check_records(repo, {"customers": {"customer": record}})
    repo.list = lambda _collection: []
    assert _check_records(repo, {"customers": {"customer": record}}) == [("customers", "customer", record)]
    with pytest.raises(Conflict, match="SOURCE_PREPARATION_INCOMPLETE"):
        _check_records(repo, {"customers": {"customer": record}}, complete=True)
    alert = {"id": "alert", "dataset_id": "dataset", "rule_id": "HIGH_VALUE", "status": "PENDING", "feedback_revision": 0}
    repo.list = lambda _collection: [{**alert, "status": "ERROR", "feedback_revision": 3, "latest_run_id": "persisted-work"}]
    assert _check_records(repo, {"alerts": {"alert": alert}}, complete=True) == []


def test_publisher_refuses_enabled_daily_control_before_any_source_write():
    from backend.publisher import _prepare_source
    settings, _approval = approved()
    repo = SimpleNamespace(settings=settings, daily_control=lambda: {"live_enabled": True})
    with pytest.raises(Conflict, match="PUBLICATION_DAILY_CONTROL_MUST_BE_DISABLED"):
        _prepare_source(repo, SimpleNamespace(manifest_hash=MANIFEST), "test-only")
