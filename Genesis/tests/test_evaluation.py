"""Local files and in-memory references only; never persist successful model doubles."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from types import MethodType, SimpleNamespace

import pytest

from scripts import capture_evaluation as evaluation


FINGERPRINT = "f" * 64


def capture_inputs(tmp_path, monkeypatch):
    cache = tmp_path / ".cache"
    cache.mkdir()
    (tmp_path / "docs").mkdir()
    junit = '<testsuites><testsuite><testcase name="pure-local-check"/></testsuite></testsuites>'
    for name in ["unit-results.xml", "integration-results.xml"]:
        (cache / name).write_text(junit)
    values = {"integration-provenance.json": {"scope": "LOCAL_EMULATOR_TEST_ONLY", "project_id": "demo-aml-insight",
            "dataset_id": "synthetic-v1-20261015", "manifest_hash": "a" * 64, "code_fingerprint": FINGERPRINT,
            "human_feedback_events": 0, "operator_uid": "PRIVATE UID", "output": {"brief": "PRIVATE NARRATIVE"},
            "reference_labels": {"secret-case": "PRIVATE LABEL"}},
        "unit-provenance.json": {"scope": "LOCAL_UNIT_TEST_ONLY", "status": "PASSED", "code_fingerprint": FINGERPRINT,
            "artifact_hash": hashlib.sha256(junit.encode()).hexdigest()},
        "python-audit.json": {"dependencies": []},
        "npm-audit.json": {"metadata": {"vulnerabilities": {}}, "vulnerabilities": {}},
        "npm-production-audit.json": {"metadata": {"vulnerabilities": {}}}}
    for name, value in values.items(): (cache / name).write_text(json.dumps(value))
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(evaluation, "code_fingerprint", lambda: FINGERPRINT)
    monkeypatch.setattr(evaluation.subprocess, "check_output", lambda args, **_kwargs: "a" * 40 if "rev-parse" in args else "")
    return cache, tmp_path / "docs/evaluation-record.json"


def test_capture_preserves_public_references_and_original_source_without_promoting_readiness(tmp_path, monkeypatch):
    _cache, target = capture_inputs(tmp_path, monkeypatch)
    release = {"genuine_investigation_run_id": "a" * 24,
        "manual_citation_grounding": {"investigation_run_id": "a" * 24, "review_status": "PASS", "reviewed_at": "2026-10-17T12:00:00Z"},
        "human_feedback_event_ids": ["b" * 24 + "-1"], "video_url": "https://example.com/demo", "video_duration_seconds": 150}
    target.write_text(json.dumps({"source": {"code_fingerprint": "c" * 64, "release_revision": "d" * 40},
        "release_evidence": release, "release_ready": True}))
    monkeypatch.setattr(evaluation, "import_release_references", lambda *_args: pytest.fail("Normal capture must not connect to cloud"))
    evaluation.capture()
    first = json.loads(target.read_text())
    assert first["release_evidence"] == evaluation.public_release_evidence(release)
    assert first["release_evidence_source"] == {"code_fingerprint": "c" * 64, "release_revision": "d" * 40}
    assert first["release_evidence_status"] == "PRESERVED_REFERENCES_UNVERIFIED" and first["release_ready"] is False
    assert first["source"]["code_fingerprint"] == FINGERPRINT
    assert "PRIVATE" not in target.read_text() and "reference_labels" not in first["local_provenance"]
    evaluation.capture()
    assert json.loads(target.read_text())["release_evidence_source"] == first["release_evidence_source"]


def test_capture_refuses_stale_unit_receipts_and_incomplete_integration_without_erasing_record(tmp_path, monkeypatch):
    cache, target = capture_inputs(tmp_path, monkeypatch)
    original = '{"release_evidence": {}}'
    target.write_text(original)
    receipt_path = cache / "unit-provenance.json"
    good = json.loads(receipt_path.read_text())
    for changes in [{"code_fingerprint": "0" * 64}, {"artifact_hash": "0" * 64}, {"status": "RUNNING"}]:
        receipt_path.write_text(json.dumps({**good, **changes}))
        with pytest.raises(ValueError, match="matching-source unit receipt"): evaluation.capture()
        assert target.read_text() == original
    receipt_path.write_text(json.dumps(good))
    (cache / "integration-results.xml").write_text('<testsuite><testcase><skipped/></testcase></testsuite>')
    with pytest.raises(ValueError, match="verification is incomplete"): evaluation.capture()
    assert target.read_text() == original


def test_capture_never_fills_genuine_evidence_from_local_fixtures(tmp_path, monkeypatch):
    _cache, target = capture_inputs(tmp_path, monkeypatch)
    evaluation.capture()
    result = json.loads(target.read_text())
    assert result["release_evidence"] == evaluation.RELEASE_DEFAULTS
    assert result["release_evidence_status"] == "NOT_RECORDED" and result["release_evidence_source"] is None
    assert result["release_ready"] is False
    for release in [{"private_output": "never copy"}, {"video_url": "https://example.com/demo?token=secret"},
        {"video_url": "https://user:password@example.com/demo"}, {"video_duration_seconds": 180},
        {"manual_citation_grounding": {"notes": "private analyst notes"}}]:
        with pytest.raises(ValueError): evaluation.public_release_evidence(release)


def test_unit_runner_binds_exact_junit_and_refuses_source_changes(tmp_path, monkeypatch):
    cache, _target = capture_inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(evaluation.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0))
    assert evaluation.run_unit() == 0
    receipt = json.loads((cache / "unit-provenance.json").read_text())
    assert receipt["status"] == "PASSED" and receipt["code_fingerprint"] == FINGERPRINT
    assert receipt["artifact_hash"] == hashlib.sha256((cache / "unit-results.xml").read_bytes()).hexdigest()
    fingerprints = iter([FINGERPRINT, "0" * 64])
    monkeypatch.setattr(evaluation, "code_fingerprint", lambda: next(fingerprints))
    with pytest.raises(ValueError, match="Source changed"): evaluation.run_unit()
    assert json.loads((cache / "unit-provenance.json").read_text())["status"] == "RUNNING"


def genuine_reference_double():
    """Pure memory fixture, including private strings that must never be exported."""
    from backend.dataset import DATASET_ID, content_hash, generate_dataset, stable_id
    from backend.engine import candidate_options, detect, enrich, prioritize, risk_assessment
    from backend.evolution import analytical_inputs, candidate_identity
    from backend.publisher import MANIFEST
    from backend.repository import Repository, now
    store, legs = {}, {}
    def put(collection, ident, row): store[collection, ident] = {"id": ident, **row}
    bundle = {"kind": "BUNDLE", "origin": "BASELINE", "component_ids": {},
        "body": {"provider": "GOOGLE_CLOUD", "code_fingerprint": FINGERPRINT}}
    bundle_id = content_hash(bundle)
    put("config_versions", bundle_id, {**bundle, "content_hash": bundle_id})
    put("datasets", DATASET_ID, {"state": "READY", "manifest_hash": MANIFEST})
    data = generate_dataset()
    case = next(case for case in data.cases.values() if case.split == "DEMO" and detect(data, case))
    alert = detect(data, case)[0]
    evidence = enrich(data, case)
    finding = {"text": "PRIVATE MODEL DOUBLE - IN MEMORY ONLY", "evidence_ids": [evidence["evidence_ids"][0]]}
    outputs = {"A1": evidence, "A2": {"findings": [finding], "counter_evidence": [], "limitations": ["Pure fixture"]},
        "A3": {"primary_typology": "OTHER", "suggested_action": "REVIEW", "rationale": finding, "uncertainty": "HIGH"},
        "A4": {"overview": finding, "key_findings": [], "counter_evidence": [], "missing_information": [],
            "next_steps": [], "limitations": ["Pure fixture"]}, "A0": prioritize(evidence, risk_assessment(evidence), "REVIEW")}
    run = {"id": "a" * 24, "dataset_id": DATASET_ID, "state": "COMPLETE", "kind": "TRIAGE_ALERT",
        "alert_id": alert["id"], "case_id": case.id, "config_bundle_id": bundle_id}
    put("pipeline_runs", run["id"], run)
    put("alerts", alert["id"], alert)
    previous = None
    steps = []
    for leg in ["A1", "A2", "A3", "A4", "A0"]:
        step = {"id": stable_id(run["id"], leg, 1), "run_id": run["id"], "leg_id": leg,
            "dataset_id": DATASET_ID, "config_bundle_id": bundle_id, "alert_id": run["alert_id"], "case_id": run["case_id"],
            "state": "SUCCEEDED", "output": outputs[leg], "input_hash": content_hash(evidence),
            "execution_provenance": "DETERMINISTIC" if leg in {"A1", "A0"} else "REAL_PROVIDER",
            "validation": {"schema_pass": True, "evidence_pass": True},
            "parent_step_ids": [previous] if previous else []}
        put("step_runs", step["id"], step)
        legs[run["id"], leg] = step["id"]
        previous = step["id"]
        steps.append(step)
    event_id = alert["id"] + "-1"
    event = {"id": event_id, "dataset_id": DATASET_ID, "provenance": "HUMAN_OPERATOR", "actor_uid": "human",
        "triage_run_id": run["id"], "alert_id": alert["id"], "case_id": run["case_id"], "revision": 1,
        "verdict": "INCONCLUSIVE", "notes": "PRIVATE UNIT NOTE"}
    put("feedback_events", event_id, event)
    body = analytical_inputs(MANIFEST, [event], steps, [alert])
    snapshot_id = content_hash(body)
    put("analytical_snapshots", snapshot_id, {"dataset_id": DATASET_ID, "body": body, "content_hash": snapshot_id})
    a5 = {"id": "d" * 24, "dataset_id": DATASET_ID, "state": "COMPLETE", "kind": "EVOLUTION",
        "config_bundle_id": bundle_id, "analytical_snapshot_id": snapshot_id}
    put("pipeline_runs", a5["id"], a5)
    a5_step = {"id": stable_id(a5["id"], "A5", 1), "run_id": a5["id"], "dataset_id": DATASET_ID,
        "config_bundle_id": bundle_id, "state": "SUCCEEDED", "execution_provenance": "REAL_PROVIDER",
        "validation": {"schema_pass": True, "evidence_pass": True}, "output": {"status": "INSUFFICIENT_EVIDENCE",
            "conclusive_reviews": 0, "target_rule_reviews": 0, "target_rule": "HIGH_VALUE", "summary": "PRIVATE MEMORY A5",
            "limitations": ["Pure unit fixture, not genuine ledger evidence"]}}
    put("step_runs", a5_step["id"], a5_step)
    legs[a5["id"], "A5"] = a5_step["id"]
    candidate = candidate_options()[0]
    candidate_hash = candidate_identity(MANIFEST, candidate)
    freeze_body = {"candidate": candidate, "candidate_hash": candidate_hash, "dataset_hash": MANIFEST,
        "evolution_run_id": a5["id"], "analytical_snapshot_id": snapshot_id, "frozen_by": "human", "activation_allowed": False}
    freeze_id = stable_id(DATASET_ID, "heldout")
    instant = now()
    freeze_hash = content_hash(freeze_body)
    put("candidate_freezes", freeze_id, {"dataset_id": DATASET_ID, **freeze_body, "content_hash": freeze_hash, "frozen_at": instant})
    put("simulations", freeze_id, {"dataset_id": DATASET_ID, "state": "COMPLETE", "freeze_id": freeze_id,
        "freeze_hash": freeze_hash, "candidate_hash": candidate_hash, "metrics": {"pure_memory_fixture": True},
        "started_at": instant + timedelta(seconds=1)})
    repo = SimpleNamespace(get=lambda collection, ident: deepcopy(store.get((collection, ident))),
        settings=SimpleNamespace(operator_uids=frozenset({"human"})))
    repo._leg_step = lambda _tx, selected, leg: repo.get("step_runs", legs[selected["id"], leg]) or {}
    repo._sealed_chain = MethodType(Repository._sealed_chain, repo)
    repo.evolution_context = MethodType(Repository.evolution_context, repo)
    private = {"expected_code_fingerprint": FINGERPRINT, "expected_manifest_hash": MANIFEST,
        "cloud_read_authorized": True, "manual_grounding_actor_uid": "human", "release_evidence": {
            "genuine_investigation_run_id": run["id"], "human_feedback_event_ids": [event_id], "genuine_a5_run_id": a5["id"],
            "manual_citation_grounding": {"investigation_run_id": run["id"], "review_status": "PASS", "reviewed_at": instant.isoformat()},
            "frozen_candidate_hash": candidate_hash, "heldout_comparison_id": freeze_id}}
    return repo, private, store, legs


def test_explicit_repository_verification_returns_references_only_and_rejects_broken_links():
    from backend.dataset import DATASET_ID, stable_id
    from backend.repository import Conflict
    repo, private, store, legs = genuine_reference_double()
    result = evaluation.verify_release_references(repo, private, FINGERPRINT)
    assert result == evaluation.public_release_evidence(private["release_evidence"])
    assert "PRIVATE" not in json.dumps(result)
    for collection, ident, changes in [
        ("pipeline_runs", "a" * 24, {"state": "FAILED"}),
        ("step_runs", legs["a" * 24, "A3"], {"execution_provenance": "UNKNOWN"}),
        ("feedback_events", private["release_evidence"]["human_feedback_event_ids"][0], {"actor_uid": "unauthorized"}),
        ("step_runs", legs["d" * 24, "A5"], {"state": "UNKNOWN_OUTCOME"}),
        ("candidate_freezes", stable_id(DATASET_ID, "heldout"), {"frozen_by": "agent"}),
        ("simulations", stable_id(DATASET_ID, "heldout"), {"freeze_hash": "mismatch"}),
    ]:
        original = store[collection, ident]
        store[collection, ident] = {**original, **changes}
        with pytest.raises((ValueError, Conflict)): evaluation.verify_release_references(repo, private, FINGERPRINT)
        store[collection, ident] = original
    with pytest.raises(ValueError): evaluation.verify_release_references(repo, {**private, "cloud_read_authorized": False}, FINGERPRINT)


def test_private_import_cannot_construct_cloud_client_under_local_settings(tmp_path, monkeypatch):
    from backend.config import Settings
    cache, _target = capture_inputs(tmp_path, monkeypatch)
    path = cache / "private-release.json"
    path.write_text(json.dumps({"cloud_read_authorized": True, "expected_code_fingerprint": FINGERPRINT}))
    monkeypatch.setattr("backend.repository.Repository", lambda *_args: pytest.fail("Local settings must refuse before ADC/client"))
    monkeypatch.setattr(Settings, "load", lambda: Settings(mode="local", project_id="demo-aml-insight",
        firestore_host="127.0.0.1:8081", auth_host="127.0.0.1:9099", live_ai=False, model_id="unused", operator_uids=frozenset()))
    with pytest.raises(ValueError, match="Verified funded disabled cloud settings"):
        evaluation.import_release_references(path, FINGERPRINT)


def test_reference_verifier_rejects_validly_hashed_wrong_source_and_developer_bundles():
    from backend.dataset import content_hash
    for run_id, changes in [("a" * 24, {"code_fingerprint": "0" * 64}),
        ("d" * 24, {"code_fingerprint": "0" * 64}), ("a" * 24, {"provider": "GEMINI_DEVELOPER_API"})]:
        repo, private, store, _legs = genuine_reference_double()
        run = store["pipeline_runs", run_id]
        bundle = store["config_versions", run["config_bundle_id"]]
        revised = {key: deepcopy(value) for key, value in bundle.items() if key not in {"id", "content_hash"}}
        revised["body"].update(changes)
        ident = content_hash(revised)
        store["config_versions", ident] = {"id": ident, "content_hash": ident, **revised}
        run["config_bundle_id"] = ident
        for (collection, _ident), row in store.items():
            if collection == "step_runs" and row["run_id"] == run_id: row["config_bundle_id"] = ident
        with pytest.raises(ValueError, match="not bound to the verified cloud source"):
            evaluation.verify_release_references(repo, private, FINGERPRINT)


def test_reference_verifier_revalidates_citations_despite_stored_success_flags():
    repo, private, store, legs = genuine_reference_double()
    store["step_runs", legs["a" * 24, "A3"]]["output"]["rationale"]["evidence_ids"] = ["invented-evidence"]
    with pytest.raises(ValueError, match="unknown source evidence"):
        evaluation.verify_release_references(repo, private, FINGERPRINT)
