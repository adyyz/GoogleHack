"""Real Auth/Firestore emulator checks; never connect to a real project."""
import os
import re

import httpx
import pytest

def _loopback_endpoint(name):
    host = os.getenv(name, "")
    match = re.fullmatch(r"127\.0\.0\.1:([0-9]{1,5})", host)
    return "http://" + host if match and 1 <= int(match[1]) <= 65535 else None


AUTH_URL = _loopback_endpoint("FIREBASE_AUTH_EMULATOR_HOST")
FIRESTORE_URL = _loopback_endpoint("FIRESTORE_EMULATOR_HOST")
pytestmark = pytest.mark.skipif(not AUTH_URL or not FIRESTORE_URL, reason="Run npm run test:integration with loopback emulators")


def test_private_discovery_scope_preserves_publication_and_denies_reserved_cases():
    from backend.config import Settings
    from backend.repository import Repository, Conflict
    repo = Repository(Settings.load())
    # This test runs after seeding when invoked alone too.
    from backend.seed import seed
    seed()
    before = repo.publication()
    discovery = repo.operator_queue('discovery')
    assert len(discovery['cases']) == 40 and all(row['split'] == 'CALIBRATION_DISCOVERY' for row in discovery['cases'])
    assert repo.publication() == before and len(repo.operator_queue()['cases']) == 12
    reserved = {row['id'] for row in repo.list('cases') if row['split'] in {'CALIBRATION_SELECTION', 'HOLDOUT'}}
    alert = next(row for row in repo.list('alerts') if row['case_id'] in reserved)
    count = len(repo.list('pipeline_runs'))
    with pytest.raises(Conflict, match='Reserved'): repo.enqueue_triage([alert['id']], 'test-only')
    with pytest.raises(Conflict, match='Reserved'): repo.alert_detail(alert['id'])
    assert len(repo.list('pipeline_runs')) == count


def test_a0_policy_transaction_uses_isolated_eligibility_double_and_preserves_versions(monkeypatch):
    """No model output or human verdict is created. Only transaction eligibility is doubled."""
    from copy import deepcopy
    from datetime import timedelta
    from types import SimpleNamespace
    from uuid import uuid4
    from backend import calibration
    from backend.config import Settings
    from backend.dataset import DATASET_ID, content_hash
    from backend.models import PolicyChangeRequest, RecommendationReviewRequest
    from backend.repository import Repository, now, Conflict
    repo = Repository(Settings.load()); client = repo.db
    prefix = 'a0_transactions_TEST_ONLY_' + uuid4().hex + '_'
    repo.db = SimpleNamespace(collection=lambda name: client.collection(prefix + name), transaction=client.transaction)
    frozen = now()
    training = [{'identity_id': str(index), 'score': .5 if index < 12 else .2,
        'verdict': 'FALSE_POSITIVE' if index < 12 else 'TRUE_POSITIVE'} for index in range(15)]
    baseline = {'tp': .25, 'fp': .65, 'cohort': None}; thresholds = {'tp': .25, 'fp': .4, 'cohort': 'TEST_ONLY'}
    forward = [{**training[index], 'identity_id': 'new-' + str(index), 'cohort': 'TEST_ONLY', 'submitted_at': frozen + timedelta(seconds=1)} for index in [0, 1, 2, 13, 14]]
    validation = {'rows': forward, 'content_hash': content_hash(forward), 'before': calibration.measured(forward, baseline, baseline),
        'after': calibration.measured(forward, thresholds, baseline), 'passed': True, 'provenance': 'PROSPECTIVE_HUMAN_REVIEWS'}
    row = {'id': uuid4().hex[:24], 'dataset_id': DATASET_ID, 'rule_id': 'HIGH_VALUE', 'state': 'PROPOSED', 'revision': 0,
        'method': calibration.METHOD, 'cohort': 'TEST_ONLY', 'training': training, 'training_hash': content_hash(training),
        'baseline': baseline, 'thresholds': thresholds, 'validation': None, 'frozen_at': frozen}
    row['candidate_hash'] = content_hash({key: row[key] for key in ('rule_id', 'thresholds', 'training_hash', 'cohort', 'method', 'baseline', 'frozen_at')})
    repo.create('auto_label_candidates', row['id'], row)
    with pytest.raises(Conflict, match='Prospective'):
        calibration.decision(repo, row['id'], RecommendationReviewRequest(expected_revision=0, state='APPROVED', notes='TEST_ONLY'), 'test', 'review')
    repo.db.collection('auto_label_candidates').document(row['id']).update({'validation': validation})
    approved = calibration.decision(repo, row['id'], RecommendationReviewRequest(expected_revision=0, state='APPROVED', notes='TEST_ONLY'), 'test', 'review')
    assert approved['state'] == 'APPROVED' and calibration.active_label_policy(repo)['revision'] == 0
    # A mechanics double cannot satisfy actual genuine feedback checks.
    with pytest.raises((KeyError, Conflict)):
        calibration.decision(repo, row['id'], PolicyChangeRequest(expected_revision=1, expected_policy_revision=0, notes='TEST_ONLY'), 'test', 'apply')
    monkeypatch.setattr(calibration, 'verify_references', lambda *_args: None)
    applied = calibration.decision(repo, row['id'], PolicyChangeRequest(expected_revision=1, expected_policy_revision=0, notes='TEST_ONLY'), 'test', 'apply')
    policy = calibration.active_label_policy(repo)
    assert policy['rules']['HIGH_VALUE'] == thresholds and policy['revision'] == 1
    version = deepcopy(repo.get('config_versions', applied['applied_policy_id']))
    # Namespaced transaction mechanics only: sealed evidence is supplied in memory,
    # never written to the model ledger or counted as a human review.
    from backend.models import ReassessmentRequest
    source = {'id': 'case', 'dataset_id': DATASET_ID, 'split': 'DEMO'}
    repo.create('cases', 'case', source)
    for index in [1, 2]:
        alert_id = str(index) * 24
        repo.create('alerts', alert_id, {'id': alert_id, 'dataset_id': DATASET_ID, 'case_id': 'case', 'rule_id': 'HIGH_VALUE',
            'status': 'COMPLETE', 'feedback_revision': index - 1, 'current_run_id': 'run', 'latest_run_id': 'run'})
    repo.create('pipeline_runs', 'run', {'id': 'run', 'dataset_id': DATASET_ID, 'config_bundle_id': 'TEST_ONLY'})
    monkeypatch.setattr(repo, '_sealed_chain', lambda *_: [{'leg_id': 'A0', 'output': {'predicted_verdict': 'AUTO_UNCERTAIN',
        'heuristic_score': .5, 'requires_context_or_protected_review': False, 'score_is_probability': False}}])
    monkeypatch.setattr(calibration, 'cohort', lambda *_: 'TEST_ONLY')
    reassessment = ReassessmentRequest(expected_revision=2, expected_policy_version=policy['policy_version_id'], notes='TEST_ONLY')
    first = calibration.reassess(repo, row['id'], reassessment, 'test')
    assert [item['state'] for item in first['items']] == ['SUCCEEDED', 'SKIPPED']
    assessment = repo.get('auto_label_assessments', first['items'][0]['assessment_id'])
    assert assessment['body']['predicted_verdict'] == 'AUTO_FP'
    assert calibration.reassess(repo, row['id'], reassessment, 'test') == first
    assert repo.get('cases', 'case') == {**source, 'schema_version': 1, 'created_at': repo.get('cases', 'case')['created_at']}
    with pytest.raises(Conflict, match='changed'):
        calibration.decision(repo, row['id'], PolicyChangeRequest(expected_revision=1, expected_policy_revision=0, notes='TEST_ONLY'), 'test', 'apply')
    rolled = calibration.decision(repo, row['id'], PolicyChangeRequest(expected_revision=2, expected_policy_revision=1, notes='TEST_ONLY'), 'test', 'rollback')
    assert rolled['state'] == 'ROLLED_BACK' and calibration.active_label_policy(repo)['policy_version_id'] == calibration.BASELINE
    assert repo.get('config_versions', applied['applied_policy_id']) == version
    restored = calibration.reassess(repo, row['id'], ReassessmentRequest(expected_revision=3, expected_policy_version=calibration.BASELINE, notes='TEST_ONLY'), 'test')
    assert restored['items'][0]['state'] == 'SUCCEEDED'
    restored_record = repo.get('auto_label_assessments', restored['items'][0]['assessment_id'])
    assert restored_record['body']['predicted_verdict'] == 'AUTO_UNCERTAIN' and restored_record['body']['restoration']
    assert repo.get('auto_label_assessments', assessment['id']) == assessment
    assert not repo.list('feedback_events') and not repo.list('step_runs')


def test_public_brief_transaction_revision_withdrawal_and_immutable_snapshot(monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4
    from backend import intelligence_api as api
    from backend.config import Settings
    from backend.repository import Repository, Conflict
    repo = Repository(Settings.load()); client = repo.db
    prefix = 'publication_TEST_ONLY_' + uuid4().hex + '_'
    repo.db = SimpleNamespace(collection=lambda name: client.collection(prefix + name), transaction=client.transaction)
    # Aggregation/validation is checked separately; this fixture tests pointer transactions.
    body = {'executive_summary': 'TEST_ONLY aggregate fixture', 'counts': {'reviewed_alerts': 0}}
    monkeypatch.setattr(api, 'publication_body', lambda *_: body)
    request = api.PublicationRequest(expected_revision=0, report_id='a' * 24, executive_summary='TEST_ONLY')
    result = api.publish(repo, request, 'test')
    published = api.public_brief(repo)
    assert published['publication']['body'] == body
    with pytest.raises(Conflict): api.publish(repo, request, 'test')
    api.withdraw(repo, api.WithdrawalRequest(expected_revision=1, notes='TEST_ONLY'), 'test')
    assert api.public_brief(repo) == {'revision': 2, 'publication': None}
    assert repo.get('evolution_publications', result['publication_id']) == published['publication']
    assert len(repo.list('audit_events')) == 2


def _reservation_input(repo, bundle_id, leg, contents):
    """Valid frozen request for ledger fault tests; never a provider response."""
    bundle = repo.get("config_versions", bundle_id)
    profile = bundle["body"]["generation_profiles"][leg]
    config = {"response_mime_type": "application/json", "automatic_function_calling": {"disable": True},
        "thinking_config": {"thinking_level": profile["thinking_level"]}, "max_output_tokens": profile["max_output_tokens"]}
    if profile["temperature"] is not None: config["temperature"] = profile["temperature"]
    if bundle["component_ids"].get("RATE_CARD"): config["service_tier"] = "standard"
    return {"contents": contents, "model_id": profile["model_id"], "generation_config": config}


def test_seed_publication_auth_and_persistence():
    from fastapi.testclient import TestClient
    from backend.api import app
    from backend.config import Settings
    from backend.dataset import DATASET_ID
    from backend.repository import Repository
    from backend.seed import seed

    seed()
    repo = Repository(Settings.load())
    manifest = repo.get("datasets", DATASET_ID)
    publication_id = repo.publication()["id"]
    seed()  # Source manifest and public snapshot remain stable across repeated seed.
    assert repo.get("datasets", DATASET_ID)["manifest_hash"] == manifest["manifest_hash"]
    assert repo.publication()["id"] == publication_id
    # Upgrade a pre-hint publication once, without rewriting frozen source records.
    customer = next(iter(repo.load_dataset().customers))
    frozen_customer = repo.get("customers", customer)
    frozen_manifest = repo.get("datasets", DATASET_ID)
    old_cases = [{key: value for key, value in case.items() if key not in {"queue_priority", "queue_reason"}} for case in repo.publication()["public_cases"]]
    repo.db.collection("publications").document(publication_id).update({"public_cases": old_cases})
    baseline_count = len(list(repo.db.collection("config_versions").stream()))
    seed()
    upgraded_id = repo.publication()["id"]
    assert upgraded_id != publication_id
    seed()
    assert repo.publication()["id"] == upgraded_id
    assert repo.get("customers", customer) == frozen_customer
    assert repo.get("datasets", DATASET_ID) == frozen_manifest
    assert len(list(repo.db.collection("config_versions").stream())) == baseline_count
    assert len(repo.load_dataset().cases) == 112
    with TestClient(app) as client:
        assert client.get("/api/health").json()["live_ai_enabled"] is False
        assert client.get("/api/config").json()["firebase_web_api_key"] is None
        assert client.get("/api/demo/dashboard").json()["case_count"] == 112
        response = client.get("/api/demo/alerts")
        assert response.headers["cache-control"] == "public, max-age=60"
        cases = response.json()["cases"]
        assert len(cases) == 12
        assert all(case["queue_priority"] and case["queue_reason"] for case in cases)
        assert "reference_labels" not in response.text
        assert "reference_reasons" not in response.text
        assert "operator-demo" not in response.text
        assert client.get("/api/demo/alerts/unpublished-case").status_code == 404
        assert client.get("/api/operator/session").status_code == 401
        assert client.get("/api/operator/audit").status_code == 401
        assert client.post("/api/operator/triage-jobs").status_code == 401
        private_routes = [(method, route.path) for route in app.routes if getattr(route, "path", "").startswith(("/api/operator/", "/api/admin/"))
            for method in route.methods if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}]
        import re
        for method, path in private_routes:
            target = re.sub(r"\{[^}]+\}", "0" * 24, path)
            for identity in [{}, {"Authorization": "Bearer invalid"}]:
                denied = client.request(method, target, headers=identity, json={} if method != "GET" else None)
                assert denied.status_code == 401, (method, path)
                assert denied.headers["cache-control"] == "no-store"
        assert client.get("/api/operator/evaluation", headers={"Authorization": "Bearer invalid"}).status_code == 401

        login = httpx.post(f"{AUTH_URL}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=emulator-only",
            json={"email": "operator@aml-insight.test", "password": "local-demo-only", "returnSecureToken": True})
        login.raise_for_status()
        headers = {"Authorization": "Bearer " + login.json()["idToken"]}
        assert client.get("/api/operator/session", headers=headers).json()["uid"] == "operator-demo"
        assert client.get("/api/operator/session", headers=headers).json()["is_admin"]
        assert client.get("/api/demo/usage").json()["total_tokens"] is None
        control = client.get("/api/operator/usage", headers=headers).json()["daily"]
        assert not control["live_enabled"]
        changed = client.put("/api/admin/usage-daily", headers=headers,
            json={"expected_revision": control["revision"], "live_enabled": False, "limit": 100})
        assert changed.status_code == 200
        assert client.put("/api/admin/usage-daily", headers=headers,
            json={"expected_revision": control["revision"], "live_enabled": False, "limit": 100}).status_code == 409
        assert client.put("/api/admin/usage-daily", headers=headers,
            json={"expected_revision": changed.json()["revision"], "live_enabled": True, "limit": 100}).status_code == 409
        assert client.put("/api/admin/usage-daily", json={"expected_revision": 0, "live_enabled": False, "limit": 100}).status_code == 401
        assert client.put("/api/admin/usage-daily", headers=headers,
            json={"expected_revision": changed.json()["revision"], "live_enabled": False, "limit": 121}).status_code == 422
        # Control-only fixture: exercise reservation floor without inventing provider output.
        daily_ref = repo.db.collection("usage_daily").document(changed.json()["day_utc"])
        daily_ref.update({"attempts_reserved": 3})
        assert client.put("/api/admin/usage-daily", headers=headers,
            json={"expected_revision": changed.json()["revision"], "live_enabled": False, "limit": 2}).status_code == 409
        daily_ref.update({"attempts_reserved": 0})
        from dataclasses import replace
        from backend.api import create_app
        with TestClient(create_app(replace(Settings.load(), admin_uids=frozenset()))) as operator_client:
            assert operator_client.get("/api/operator/session", headers=headers).json()["is_admin"] is False
            assert operator_client.get("/api/operator/usage", headers=headers).status_code == 200
            assert operator_client.put("/api/admin/usage-daily", headers=headers,
                json={"expected_revision": changed.json()["revision"], "live_enabled": False, "limit": 99}).status_code == 403
        audit = client.get("/api/operator/audit?limit=1", headers=headers).json()
        assert len(audit["items"]) == 1
        if audit["next_cursor"]:
            following = client.get('/api/operator/audit', params={"cursor": audit["next_cursor"], "limit": 1}, headers=headers).json()
            assert all(row["id"] != audit["items"][0]["id"] for row in following["items"])
        assert client.post("/api/operator/triage-jobs", headers=headers).status_code == 422
        multi = next(case for case in cases if len(case["alerts"]) > 1)
        alert_ids = [alert["id"] for alert in multi["alerts"]]
        assert client.post("/api/operator/triage-jobs", headers=headers, json={"alert_ids": alert_ids[:1]}).status_code == 422
        assert client.post("/api/operator/triage-jobs", headers=headers, json={"alert_ids": [alert_ids[0]] * 2}).status_code == 422
        # Concurrent enqueues share a parent before the local worker starts.
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            enqueues = list(pool.map(lambda _: repo.enqueue_triage(alert_ids, "operator-demo"), range(2)))
        assert enqueues[0][0] == enqueues[1][0]
        assert sum(created for _, created in enqueues) == 1
        queued = client.post("/api/operator/triage-jobs", headers=headers, json={"alert_ids": alert_ids}).json()
        assert queued["state"] == "QUEUED"
        from backend.jobs import run_local
        run_local(repo, queued["id"])
        failed = client.get(f'/api/operator/runs/{queued["id"]}', headers=headers).json()
        assert failed["state"] == "FAILED" and failed["error_code"] == "AI_NOT_CONNECTED"
        assert len(failed["children"]) == len(alert_ids)
        assert len(failed["attempts"]) == 2 * len(alert_ids)
        assert {step["leg_id"] for step in failed["attempts"]} == {"A1", "A2"}
        assert all(step["usage_status"] == "NOT_APPLICABLE" and step["total_tokens"] is None for step in failed["attempts"])
        for ident in alert_ids:
            private = client.get(f'/api/operator/alerts/{ident}', headers=headers).json()
            assert private["latest_run"]["error_code"] == "AI_NOT_CONNECTED"
            assert private["alert"]["status"] == "PENDING" and not private["alert"]["current_run_id"]
            assert private["outputs"] == {}
        assert client.get("/api/operator/usage", headers=headers).json()["daily"]["attempts_reserved"] == 0
        public_usage = client.get("/api/demo/usage")
        assert public_usage.json()["not_applicable_attempts"] == 2 * len(alert_ids)
        for private_key in ["case_id", "alert_id", "provider_usage_raw", "provider_request_id", "output", "operator-demo"]:
            assert private_key not in public_usage.text
        assert client.get("/api/operator/runs?limit=1", headers=headers).json()["next_cursor"]
        assert client.get(f'/api/operator/alerts/{alert_ids[0]}/feedback', headers=headers).json()["items"] == []
        terminal = client.post("/api/operator/triage-jobs", headers=headers, json={"alert_ids": alert_ids})
        assert terminal.status_code == 200 and terminal.json()["state"] == "FAILED"
        diagnostic = client.get("/api/operator/evaluation", headers=headers)
        assert diagnostic.status_code == 200
        assert len(diagnostic.json()["discovery_preview"]) == 3
        assert all(row["split"] == "CALIBRATION_DISCOVERY" for row in diagnostic.json()["discovery_preview"])

        alert = next(c["alerts"][0] for c in cases if c["alerts"])
        result = client.post(f'/api/operator/alerts/{alert["id"]}/feedback', headers=headers,
            json={"verdict": "INCONCLUSIVE", "notes": "Missing validated AI output", "expected_revision": 0})
        assert result.status_code == 409  # No fake completed run can accept feedback.
        assert repo.list("feedback_events") == []

        snapshot_url = "/api/operator/evolution/snapshots"
        assert client.post(snapshot_url).status_code == 401
        assert client.get(snapshot_url).status_code == 401
        first_snapshot = client.post(snapshot_url, headers=headers)
        assert first_snapshot.status_code == 200
        snapshot = first_snapshot.json()
        assert snapshot["body"]["sample_sizes"]["conclusive_reviews"] == 0
        assert snapshot["body"]["detector_gate"]["status"] == "INSUFFICIENT_EVIDENCE"
        assert snapshot["body"]["usage"]["total_tokens"] is None
        assert snapshot["body"]["succeeded_steps"]  # Real deterministic A1 records only.
        assert client.post(snapshot_url, headers=headers).json() == snapshot
        history = client.get(snapshot_url + "?limit=1", headers=headers).json()
        assert history["items"][0]["id"] == snapshot["id"] and history["next_cursor"] is None
        assert client.get(snapshot_url + "?limit=101", headers=headers).status_code == 422
        freezes = [event for event in repo.list("audit_events") if event["action"] == "ANALYTICAL_INPUTS_FROZEN"]
        assert len(freezes) == 1
        assert "reference_labels" not in first_snapshot.text and "reference_reasons" not in first_snapshot.text
        a5_url = "/api/operator/evolution/runs"
        assert client.post(a5_url, json={"snapshot_id": snapshot["id"]}).status_code == 401
        before_a5 = len(repo.list("pipeline_runs"))
        absent_feedback = client.post(a5_url, headers=headers, json={"snapshot_id": snapshot["id"]})
        assert absent_feedback.status_code == 409 and "Genuine analyst feedback" in absent_feedback.text
        assert len(repo.list("pipeline_runs")) == before_a5
        assert client.post(a5_url, headers=headers, json={"snapshot_id": "0" * 64}).status_code == 404
        freeze_url = "/api/operator/evolution/freezes"
        option = diagnostic.json()["freeze_options"][0]
        freeze_request = {"candidate_id": option["candidate"]["id"], "expected_candidate_hash": option["candidate_hash"],
            "evolution_run_id": "0" * 24, "notes": "Refusal boundary test; no actual selection"}
        assert client.post(freeze_url, json=freeze_request).status_code == 401
        assert client.post(freeze_url, headers=headers, json=freeze_request).status_code == 409
        assert client.post(freeze_url, headers=headers, json={**freeze_request, "expected_candidate_hash": "0" * 64}).status_code == 409
        assert repo.list("candidate_freezes") == [] and repo.list("simulations") == []
        assert client.post(freeze_url + "/missing/simulation", headers=headers).status_code == 404
        assert client.get(a5_url + "/missing", headers=headers).status_code == 404
        assert client.get(a5_url, headers=headers).json()["items"] == []
        assert client.get(a5_url).status_code == 401
        assert client.get("/api/operator/evolution/freeze", headers=headers).json() == {"freeze": None, "simulation": None}
        assert client.get("/api/operator/evolution/freeze").status_code == 401
        candidates = client.get("/api/operator/evolution/candidates", headers=headers)
        assert candidates.status_code == 200 and len(candidates.json()["options"]) == 3
        assert candidates.headers["cache-control"] == "no-store" and "Authorization" in candidates.headers["vary"]
        assert client.get("/api/operator/evolution/candidates").status_code == 401
        review_url = "/api/operator/evolution/recommendations/missing/review"
        review = {"expected_revision": 0, "state": "APPROVED", "notes": "No proposal exists"}
        assert client.put(review_url, json=review).status_code == 401
        assert client.put(review_url, headers=headers, json=review).status_code == 404

        signup = httpx.post(f"{AUTH_URL}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=emulator-only",
            json={"returnSecureToken": True})
        signup.raise_for_status()
        assert client.get("/api/operator/session", headers={"Authorization": "Bearer " + signup.json()["idToken"]}).status_code == 403
        unauthorized = {"Authorization": "Bearer " + signup.json()["idToken"]}
        for method, path in private_routes:
            target = re.sub(r"\{[^}]+\}", "0" * 24, path)
            assert client.request(method, target, headers=unauthorized, json={} if method != "GET" else None).status_code == 403, (method, path)
        # Admin membership cannot grant access without operator membership.
        with TestClient(create_app(replace(Settings.load(), operator_uids=frozenset(), admin_uids=frozenset({"operator-demo"})))) as admin_only:
            assert admin_only.get("/api/operator/session", headers=headers).status_code == 403
            assert admin_only.put("/api/admin/usage-daily", headers=headers,
                json={"expected_revision": 0, "live_enabled": False, "limit": 1}).status_code == 403
        assert client.post(snapshot_url, headers={"Authorization": "Bearer " + signup.json()["idToken"]}).status_code == 403

    denial = httpx.get(f"{FIRESTORE_URL}/v1/projects/demo-aml-insight/databases/(default)/documents/customers")
    assert denial.status_code == 403
    base = f"{FIRESTORE_URL}/v1/projects/demo-aml-insight/databases/(default)/documents/"
    for collection in ["datasets", "step_runs", "feedback_events", "analytical_snapshots", "candidate_freezes", "simulations", "config_versions"]:
        for identity in [{}, headers]:
            assert httpx.get(base + collection, headers=identity).status_code == 403
    for collection in ["step_runs", "feedback_events", "usage_daily", "candidate_freezes", "config_versions"]:
        assert httpx.patch(base + collection + "/denied-privacy-probe", headers=headers,
            json={"fields": {"probe": {"stringValue": "must-not-write"}}}).status_code == 403
    from pathlib import Path
    import json
    from scripts.capture_evaluation import code_fingerprint
    Path(".cache").mkdir(exist_ok=True)
    Path(".cache/integration-provenance.json").write_text(json.dumps({"scope": "LOCAL_EMULATOR_TEST_ONLY",
        "project_id": "demo-aml-insight", "dataset_id": DATASET_ID, "manifest_hash": manifest["manifest_hash"],
        "baseline_bundle_id": repo.ensure_baseline(), "publication_id": upgraded_id,
        "code_fingerprint": code_fingerprint(), "private_routes_checked": len(private_routes),
        "human_feedback_events": len(repo.list("feedback_events")), "genuine_model_results_created": 0,
        "candidate_freezes_created": 0, "heldout_comparisons_created": 0}), encoding="utf-8")


def test_attempt_reservation_is_atomic_and_fail_closed(monkeypatch):
    """Cloud gate settings are a local fixture; no cloud client or model is invoked."""
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace
    from datetime import timedelta
    from uuid import uuid4

    from backend.config import Settings
    from backend.dataset import DATASET_ID, stable_id
    from backend.gateway import call_model
    from backend.models import DailyControlRequest, PipelineRun, StepRun
    from backend.repository import Conflict, Repository, now

    repo = Repository(Settings.load())  # Establish emulator client before injecting gate-only settings.
    local_settings = repo.settings
    instant = now()
    repo.settings = replace(local_settings, mode="cloud", live_ai=True, credits_verified=True,
        credit_verified_until=instant + timedelta(days=3), verified_cloud_model_id=local_settings.model_id,
        verified_cloud_location="global", deployed_code_fingerprint="a" * 64)
    bundle_id = repo.ensure_baseline()
    run_ids, leases = [uuid4().hex for _ in range(3)], []
    for run_id in run_ids:
        repo.create("pipeline_runs", run_id, PipelineRun(id=run_id, dataset_id=DATASET_ID, kind="EVOLUTION",
            config_bundle_id=bundle_id, actor_uid="reservation-test").model_dump())
        delivery = repo.prepare_dispatch(run_id)
        leases.append(repo.claim_delivery(run_id, delivery["generation"], "reservation-test-owner")["lease"])

    def step(number):
        run_id = run_ids[number - 1]
        from backend.dataset import content_hash
        request = _reservation_input(repo, bundle_id, "A5", "reservation-test-input")
        return StepRun(id=stable_id(run_id, "A5", 1), dataset_id=DATASET_ID, run_id=run_id,
            leg_id="A5", attempt_number=1, config_bundle_id=bundle_id, state="STARTED",
            model_id=repo.settings.model_id, started_at=instant, input_hash=content_hash(request), input_snapshot=request,
            usage_status="UNKNOWN", cost_status="UNKNOWN", worker_lease=leases[number - 1])

    def control(enabled, limit):
        return repo.update_daily_control(DailyControlRequest(expected_revision=repo.daily_control()["revision"],
            live_enabled=enabled, limit=limit), "operator-demo")

    def attempt(number):
        try: return repo.reserve_model_attempt(step(number))
        except Conflict as exc: return str(exc)

    # Matching input hashes cannot legitimize a request that changes a frozen profile.
    from copy import deepcopy
    from backend.dataset import content_hash
    altered = step(1)
    request = deepcopy(altered.input_snapshot)
    request["generation_config"]["temperature"] = 0.9
    with pytest.raises(Conflict, match="CONFIG_GENERATION_MISMATCH"):
        repo.reserve_model_attempt(altered.model_copy(update={"input_snapshot": request, "input_hash": content_hash(request)}))
    assert repo.get("step_runs", altered.id) is None
    control(False, 1)
    assert attempt(1) == "LIVE_AI_DISABLED"
    assert repo.get("step_runs", step(1).id) is None
    control(True, 1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [1, 2]))
    assert results.count(True) == 1 and results.count("CAP_REACHED") == 1
    winner = results.index(True) + 1
    loser = 3 - winner
    assert attempt(winner) is False
    assert repo.daily_control()["attempts_reserved"] == 1
    assert repo.get("step_runs", step(loser).id) is None
    stored = repo.get("step_runs", step(winner).id)
    assert stored["state"] == "STARTED" and stored["output"] is None and stored["total_tokens"] is None
    # A reservation has no invented provider result; completion remains the gateway's job.
    control(False, 2)
    assert attempt(loser) == "LIVE_AI_DISABLED"
    control(True, 2)
    repo.settings = replace(repo.settings, credit_verified_until=instant - timedelta(seconds=1))
    assert attempt(loser) == "AI_NOT_CONNECTED"
    repo.settings = replace(repo.settings, credit_verified_until=instant + timedelta(days=3))
    repo.db.collection("usage_daily").document(instant.date().isoformat()).update({"credit_verified_until": instant - timedelta(seconds=1)})
    assert attempt(loser) == "CREDIT_VERIFICATION_EXPIRED"
    control(True, 2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        duplicates = list(pool.map(attempt, [loser, loser]))
    assert duplicates.count(True) == 1 and duplicates.count(False) == 1
    assert repo.daily_control()["attempts_reserved"] == 2
    assert attempt(3) == "CAP_REACHED"  # Different runs share the same atomic cap.
    control(False, 2)
    monkeypatch.setattr("backend.repository.now", lambda: instant + timedelta(days=1))
    assert repo.daily_control()["live_enabled"] is False
    assert repo.daily_control()["attempts_reserved"] == 0
    assert attempt(3) == "LIVE_AI_DISABLED"
    assert repo.get("step_runs", step(3).id) is None
    repo.settings = local_settings
    assert call_model(repo.settings).outcome == "NOT_SENT"


def test_opt_in_worker_queues_claims_and_preserves_unknown_outcome(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace
    from datetime import timedelta
    from types import SimpleNamespace
    from fastapi.testclient import TestClient

    from backend.api import create_app
    from backend.config import Settings
    from backend.jobs import worker_once
    from backend.models import DailyControlRequest, FeedbackRequest
    from backend.repository import Conflict, Repository, now

    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-credential")
    settings = replace(Settings.load(), local_gemini_enabled=True, local_gemini_free_verified=True,
        local_gemini_verified_until=now() + timedelta(hours=1))
    repo = Repository(settings)
    calls = []

    class FaultClient:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        @property
        def models(self): return self
        def count_tokens(self, **_request): return SimpleNamespace(total_tokens=50)
        def generate_content(self, **_request):
            calls.append("generation")
            raise TimeoutError("private-key-or-source-text-must-not-be-stored")

    monkeypatch.setattr("backend.gateway._provider_client", lambda _settings: FaultClient())
    login = httpx.post(f"{AUTH_URL}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=emulator-only",
        json={"email": "operator@aml-insight.test", "password": "local-demo-only", "returnSecureToken": True})
    login.raise_for_status()
    headers = {"Authorization": "Bearer " + login.json()["idToken"]}
    case = next(case for case in repo.publication()["public_cases"] if len(case["alerts"]) == 1)
    alert_id = case["alerts"][0]["id"]
    daily = repo.daily_control()
    reserved_before = daily["attempts_reserved"]
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=True, limit=12), "operator-demo")
    with TestClient(create_app(settings)) as client:
        queued = client.post("/api/operator/triage-jobs", headers=headers, json={"alert_ids": [alert_id]})
        assert queued.status_code == 200 and queued.json()["state"] == "QUEUED"
        assert queued.json()["attempts"] == [] and calls == []
        parent_id = queued.json()["id"]
        assert client.post("/api/operator/triage-jobs", headers=headers, json={"alert_ids": [alert_id]}).json()["id"] == parent_id
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda _: repo.claim_batch(parent_id), range(2)))
        assert claims.count(True) == 1 and claims.count(False) == 1
        assert worker_once(repo) == 0  # Another process cannot claim RUNNING work.
        # Restore only queue state to exercise the actual separate worker entry point.
        repo.db.collection("pipeline_runs").document(parent_id).update({"state": "QUEUED"})
        assert worker_once(repo) == 1
        failed = client.get(f'/api/operator/runs/{parent_id}', headers=headers).json()
        assert failed["state"] == "FAILED" and failed["error_code"] == "PROVIDER_OUTCOME_UNKNOWN"
        assert {step["leg_id"] for step in failed["attempts"]} == {"A1", "A2"}
        a2 = next(step for step in failed["attempts"] if step["leg_id"] == "A2")
        stored = repo.get("step_runs", a2["id"])
        assert stored["state"] == "UNKNOWN_OUTCOME" and stored["output"] is None
        assert stored["prompt_version_id"] and stored["context_version_id"] and stored["risk_version_id"]
        assert "private-key" not in str(stored)
        assert worker_once(repo) == 0 and calls == ["generation"]
        assert repo.daily_control()["attempts_reserved"] == reserved_before + 1
        detail = repo.alert_detail(alert_id)
        assert detail["alert"]["status"] == "ERROR" and detail["alert"]["current_run_id"] is None
        assert client.post(f'/api/operator/alerts/{alert_id}/feedback', headers=headers,
            json={"verdict": "INCONCLUSIVE", "notes": "Still incomplete", "expected_revision": 0}).status_code == 409
        child_id = failed["children"][0]["id"]
        child_ref = repo.db.collection("pipeline_runs").document(child_id)
        alert_ref = repo.db.collection("alerts").document(alert_id)
        child_ref.update({"state": "RUNNING"})
        with pytest.raises(Conflict, match="incomplete"): repo.complete_alert(child_id)
        # A forged COMPLETE projection cannot turn unknown output into human-review evidence.
        child_ref.update({"state": "COMPLETE"})
        alert_ref.update({"status": "COMPLETE", "current_run_id": child_id})
        assert client.get(f'/api/operator/alerts/{alert_id}', headers=headers).status_code == 409
        with pytest.raises(Conflict, match="incomplete"):
            repo.save_feedback(alert_id, FeedbackRequest(verdict="INCONCLUSIVE", notes="Fixture guard check", expected_revision=0), "operator-demo")
        child_ref.update({"state": "FAILED"})
        alert_ref.update({"status": "ERROR", "current_run_id": None})
    daily = repo.daily_control()
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=False, limit=12), "operator-demo")


def test_leased_runner_seals_closed_multi_alert_work_without_transport():
    from backend.config import Settings
    from backend.worker import execute_delivery
    from backend.repository import Repository
    repo = Repository(Settings.load())
    case = next(item for item in repo.publication()["public_cases"] if len(item["alerts"]) > 1)
    parent_id, created = repo.enqueue_triage([item["id"] for item in case["alerts"]], "closed-delivery-fixture")
    assert created
    task = repo.prepare_dispatch(parent_id)
    lease = repo.claim_delivery(parent_id, task["generation"], "closed-multi-owner")["lease"]
    before = repo.daily_control()["attempts_reserved"]
    assert execute_delivery(repo, lease) == {"status": "TERMINAL", "state": "FAILED"}
    detail = repo.run_detail(parent_id)
    assert detail["state"] == "FAILED" and detail["error_code"] == "AI_NOT_CONNECTED"
    assert len(detail["children"]) == len(case["alerts"])
    assert all(child["state"] == "FAILED" for child in detail["children"])
    assert len(detail["attempts"]) == 2 * len(case["alerts"])
    assert {row["leg_id"] for row in detail["attempts"]} == {"A1", "A2"}
    assert all(row["total_tokens"] is None and row["usage_status"] == "NOT_APPLICABLE" for row in detail["attempts"])
    assert repo.daily_control()["attempts_reserved"] == before
    assert repo.claim_delivery(parent_id, task["generation"], "duplicate-closed-owner")["status"] == "TERMINAL"


def test_delivery_generations_lease_fencing_and_unknown_attempt_recovery(monkeypatch):
    """Real emulator transactions; no transport, successful AI output or human review."""
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace
    from datetime import timedelta
    from uuid import uuid4
    from backend.config import Settings
    from backend.dataset import DATASET_ID, content_hash, stable_id
    from backend.models import DailyControlRequest, PipelineRun, StepRun
    from backend.repository import Conflict, Repository, now

    monkeypatch.setenv("GEMINI_API_KEY", "unit-fixture-never-sent")
    settings = replace(Settings.load(), local_gemini_enabled=True, local_gemini_free_verified=True,
        local_gemini_verified_until=now() + timedelta(hours=1))
    repo = Repository(settings)
    instant = now()
    case = next(item for item in repo.publication()["public_cases"] if len(item["alerts"]) == 1)
    run_id, created = repo.enqueue_triage([item["id"] for item in case["alerts"]], "delivery-fixture")
    assert created
    parent = repo.get("pipeline_runs", run_id)
    child_id = parent["child_run_ids"][0]
    child = repo.get("pipeline_runs", child_id)
    bundle = child["config_bundle_id"]
    delivery = repo.prepare_dispatch(run_id)
    repo.record_dispatch(run_id, delivery["generation"], "UNKNOWN")
    assert repo.prepare_dispatch(run_id) == delivery
    repo.record_dispatch(run_id, delivery["generation"], "FAILED")
    failed_send = repo.run_detail(run_id)
    assert failed_send["state"] == "QUEUED" and failed_send["error_code"] == "DISPATCH_FAILED"
    assert all(item["state"] == "QUEUED" for item in failed_send["children"])
    same_id, duplicate_created = repo.enqueue_triage([item["id"] for item in case["alerts"]], "dispatch-retry-fixture")
    assert same_id == run_id and not duplicate_created
    current = repo.prepare_dispatch(run_id)
    assert repo.get("pipeline_runs", run_id)["child_run_ids"] == parent["child_run_ids"]
    assert current["generation"] == delivery["generation"] + 1 and current["task_id"] != delivery["task_id"]
    assert repo.claim_delivery(run_id, delivery["generation"], "old-generation")["status"] == "STALE"
    with pytest.raises(Conflict, match="GENERATION_CHANGED"): repo.record_dispatch(run_id, delivery["generation"], "SENT")
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda owner: repo.claim_delivery(run_id, current["generation"], owner), ["first-owner", "duplicate-owner"]))
    assert sorted(row["status"] for row in claims) == ["BUSY", "CLAIMED"]
    lease = next(row["lease"] for row in claims if row["lease"])
    assert (lease.expires_at - lease.execution_deadline_at).total_seconds() == 60
    stored_run = repo.get("pipeline_runs", run_id)
    assert (lease.expires_at - stored_run["started_at"]).total_seconds() == 300
    assert not repo.claim_batch(run_id)  # One-shot worker cannot steal dispatched work.
    repo.record_dispatch(run_id, current["generation"], "UNKNOWN")
    assert repo.get("pipeline_runs", run_id)["dispatch_state"] == "SENT"
    from backend.engine import enrich
    data = repo.load_dataset()
    evidence = enrich(data, data.cases[child["case_id"]])
    a1_id = stable_id(child_id, "A1", 1)
    repo.worker_update(lease, child_id, {"state": "RUNNING", "stage": "A1"}, alert_state="RUNNING")
    repo.create("step_runs", a1_id, StepRun(id=a1_id, dataset_id=DATASET_ID, run_id=child_id, leg_id="A1",
        case_id=child["case_id"], alert_id=child["alert_id"], config_bundle_id=bundle, state="SUCCEEDED",
        started_at=instant, finished_at=instant, input_hash=content_hash(evidence), output=evidence,
        validation={"schema_pass": True, "evidence_pass": True}).model_dump())
    frozen_a1_hash = content_hash(repo.get("step_runs", a1_id))
    repo.worker_update(lease, child_id, {"stage": "A2", "checkpoint_step_id": a1_id})
    with pytest.raises(Conflict, match="NOT_TERMINAL"):
        repo.worker_update(lease, run_id, {"state": "FAILED"}, finishing=True)
    daily = repo.daily_control()
    reserved_before = daily["attempts_reserved"]
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=True, limit=12), "operator-demo")
    def step(number, worker_lease=lease):
        request = _reservation_input(repo, bundle, "A2", "fault-fixture")
        return StepRun(id=stable_id(child_id, "A2", number), dataset_id=DATASET_ID, run_id=child_id, leg_id="A2",
            alert_id=child["alert_id"], case_id=child["case_id"], parent_step_ids=[a1_id],
            attempt_number=number, config_bundle_id=bundle, state="STARTED", model_id=settings.active_model_id,
            started_at=instant, input_hash=content_hash(request), input_snapshot=request,
            usage_status="UNKNOWN", cost_status="UNKNOWN", worker_lease=worker_lease)
    assert repo.reserve_model_attempt(step(1))
    with pytest.raises(Conflict, match="STILL_OWNED"): repo.recover_started_attempt(lease, step(1).id)
    monkeypatch.setattr("backend.repository.now", lambda: stored_run["started_at"] + timedelta(seconds=241))
    with pytest.raises(Conflict, match="EXECUTION_BOUND"): repo.worker_update(lease, run_id, {"stage": "A5"})
    with pytest.raises(Conflict, match="EXECUTION_BOUND"): repo.reserve_model_attempt(step(2))
    repo.worker_update(lease, run_id, {"error_code": "WORKER_EXECUTION_BOUND"}, finishing=True)
    monkeypatch.setattr("backend.repository.now", lambda: stored_run["started_at"] + timedelta(seconds=301))
    resumed = repo.claim_delivery(run_id, current["generation"], "recovery-owner")["lease"]
    assert resumed is not None and repo.get("pipeline_runs", run_id)["lease_claim_count"] == 2
    assert repo.get("pipeline_runs", child_id)["checkpoint_step_id"] == a1_id
    assert repo.recover_started_attempt(resumed, a1_id)["state"] == "SUCCEEDED"
    assert content_hash(repo.get("step_runs", a1_id)) == frozen_a1_hash
    with pytest.raises(Conflict, match="LEASE_LOST"): repo.worker_update(lease, run_id, {"stage": "A5"})
    with pytest.raises(Conflict, match="LEASE_LOST"): repo.reserve_model_attempt(step(2))
    from backend.jobs import run_delivery
    def never_send(*_args, **_kwargs): raise AssertionError("A resumed STARTED/unknown step must never call transport")
    monkeypatch.setattr("backend.jobs.triage_leg", never_send)
    run_delivery(repo, resumed)
    unknown = repo.get("step_runs", step(1).id)
    assert unknown["state"] == "UNKNOWN_OUTCOME" and unknown["output"] is None
    assert content_hash(repo.get("step_runs", a1_id)) == frozen_a1_hash
    assert repo.get("pipeline_runs", run_id)["state"] == "FAILED"
    assert {row["leg_id"] for row in repo.usage_steps(child_id)} == {"A1", "A2"}
    # A late failed transport response is retained privately without reopening the
    # sealed unknown step, changing a model outcome or reserving another attempt.
    assert not repo.seal_provider_attempt(step(1), {"state": "FAILED", "output": None, "error_code": "PROVIDER_HTTP_401"})
    sealed = repo.get("step_runs", step(1).id)
    assert sealed["state"] == "UNKNOWN_OUTCOME" and sealed["output"] is None and sealed["total_tokens"] is None
    before = content_hash(sealed)
    assert not repo.seal_provider_attempt(step(1), {"state": "FAILED", "output": None, "error_code": "PROVIDER_HTTP_429"})
    assert content_hash(repo.get("step_runs", step(1).id)) == before
    assert repo.reserve_model_attempt(step(1)) is False
    assert repo.daily_control()["attempts_reserved"] == reserved_before + 1
    assert repo.claim_delivery(run_id, current["generation"], "terminal-duplicate")["status"] == "TERMINAL"
    daily = repo.daily_control()
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=False, limit=12), "operator-demo")


def test_dispatch_unknown_and_duplicate_ack_preserve_persisted_task_identity(monkeypatch):
    """Real demo Firestore ledger, in-memory task transport; no cloud API requests."""
    from dataclasses import replace
    from datetime import timedelta
    from types import SimpleNamespace
    from google.api_core.exceptions import AlreadyExists
    from backend.config import Settings
    from backend.dispatch import dispatch_run
    from backend.repository import Repository, now

    repo = Repository(Settings.load())
    case = next(item for item in repo.publication()["public_cases"] if len(item["alerts"]) == 1)
    run_id, created = repo.enqueue_triage([item["id"] for item in case["alerts"]], "dispatch-fault-fixture")
    assert created
    before = repo.daily_control()["attempts_reserved"]
    # Only the dispatch settings are synthetic. All actual database operations
    # retain the already-created loopback demo client; never construct a cloud repo.
    settings = replace(repo.settings, mode="cloud", project_id="unit-project", live_ai=True, credits_verified=True,
        credit_verified_until=now() + timedelta(minutes=5), cloud_tasks_enabled=True,
        worker_audience="https://unit-worker.run.app", task_invoker_email="tasks@unit-project.iam.gserviceaccount.com",
        task_queue_path="projects/unit-project/locations/test-region/queues/unit-queue",
        verified_cloud_model_id=repo.settings.model_id, verified_cloud_location="global")
    dispatcher = SimpleNamespace(settings=settings, get=repo.get, prepare_dispatch=repo.prepare_dispatch, record_dispatch=repo.record_dispatch)
    calls = []
    class Client:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def create_task(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1: raise TimeoutError("unknown task creation outcome")
            raise AlreadyExists("persisted identity already known")
    monkeypatch.setattr("backend.dispatch.tasks_v2.CloudTasksClient", Client)
    dispatch_run(dispatcher, run_id)
    unknown = repo.get("pipeline_runs", run_id)
    assert unknown["state"] == "QUEUED" and unknown["dispatch_state"] == "UNKNOWN"
    assert unknown["error_code"] == "DISPATCH_OUTCOME_UNKNOWN"
    dispatch_run(dispatcher, run_id)
    acknowledged = repo.get("pipeline_runs", run_id)
    assert acknowledged["dispatch_state"] == "SENT" and acknowledged["error_code"] is None
    assert acknowledged["dispatch_generation"] == unknown["dispatch_generation"]
    assert calls[0]["task"] == calls[1]["task"]
    dispatch_run(dispatcher, run_id)
    assert len(calls) == 2 and repo.daily_control()["attempts_reserved"] == before
    lease = repo.claim_delivery(run_id, acknowledged["dispatch_generation"], "dispatch-closed-owner")["lease"]
    from backend.jobs import run_delivery
    run_delivery(repo, lease)
    assert repo.run_detail(run_id)["state"] == "FAILED"
    assert repo.daily_control()["attempts_reserved"] == before


def test_known_transient_retry_has_distinct_reservation_and_stops_on_unknown(monkeypatch):
    from dataclasses import replace
    from datetime import timedelta
    from types import SimpleNamespace
    from google.genai.errors import ClientError
    from backend.config import Settings
    from backend.dataset import stable_id
    from backend.jobs import worker_once
    from backend.models import DailyControlRequest
    from backend.repository import Repository, now

    monkeypatch.setenv("GEMINI_API_KEY", "test-only-never-sent")
    settings = replace(Settings.load(), local_gemini_enabled=True, local_gemini_free_verified=True,
        local_gemini_verified_until=now() + timedelta(minutes=5))
    repo = Repository(settings)
    calls = []
    class FaultClient:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        @property
        def models(self): return self
        def count_tokens(self, **_kwargs): return SimpleNamespace(total_tokens=50)
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise ClientError(429, {"error": {"status": "RESOURCE_EXHAUSTED", "details": [
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "1s"}]}})
            raise TimeoutError("private transport details")
    monkeypatch.setattr("backend.gateway._provider_client", lambda _settings: FaultClient())
    daily = repo.daily_control()
    before = daily["attempts_reserved"]
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=True, limit=12), "operator-demo")
    case = next(item for item in repo.publication()["public_cases"] if len(item["alerts"]) == 1)
    run_id, created = repo.enqueue_triage([item["id"] for item in case["alerts"]], "retry-fault-fixture")
    assert created and worker_once(repo) == 1
    detail = repo.run_detail(run_id)
    child_id = detail["children"][0]["id"]
    attempts = [row for row in detail["attempts"] if row["leg_id"] == "A2"]
    assert detail["state"] == "FAILED" and detail["error_code"] == "PROVIDER_OUTCOME_UNKNOWN"
    assert len(attempts) == 2 and len(calls) == 2 and calls[0] == calls[1]
    assert attempts[0]["state"] == "FAILED" and attempts[1]["state"] == "UNKNOWN_OUTCOME"
    assert attempts[1]["retry_of_step_id"] == attempts[0]["id"]
    assert all(repo.get("step_runs", row["id"])["output"] is None for row in attempts)
    assert repo.get("pipeline_runs", child_id)["checkpoint_step_id"] == attempts[1]["id"]
    assert repo.get("step_runs", stable_id(child_id, "A2", 3)) is None
    assert {row["leg_id"] for row in detail["attempts"]} == {"A1", "A2"}
    assert repo.daily_control()["attempts_reserved"] == before + 2
    assert worker_once(repo) == 0 and len(calls) == 2
    daily = repo.daily_control()
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=False, limit=12), "operator-demo")


def test_authenticated_http_delivery_runs_real_subprocess_once(monkeypatch):
    """Local signed JWT/certs and demo emulators; no cloud identity or model call."""
    import json
    from dataclasses import replace
    from types import SimpleNamespace
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from fastapi.testclient import TestClient
    from google.auth import crypt, jwt
    from backend.config import Settings
    from backend.repository import Repository, now
    from backend.worker import create_app

    repo = Repository(Settings.load())
    case = next(item for item in repo.publication()["public_cases"] if len(item["alerts"]) > 1)
    run_id, created = repo.enqueue_triage([item["id"] for item in case["alerts"]], "http-delivery-fixture")
    assert created
    task = repo.prepare_dispatch(run_id)
    repo.record_dispatch(run_id, task["generation"], "FAILED")
    retry = repo.prepare_dispatch(run_id)
    settings = replace(repo.settings, mode="cloud", project_id="unit-project", worker_audience="https://unit-worker.run.app",
        task_invoker_email="tasks@unit-project.iam.gserviceaccount.com")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    signer = crypt.RSASigner.from_string(pem, key_id="local-http-only")
    certs = SimpleNamespace(status=200, data=json.dumps({"local-http-only": public.decode()}).encode())
    monkeypatch.setattr("backend.worker.GoogleRequest", lambda: lambda *_args, **_kwargs: certs)
    made = []
    def local_repo(_settings):
        made.append(True)
        return repo  # The real client stays pinned to loopback demo-aml-insight.
    monkeypatch.setattr("backend.worker.Repository", local_repo)
    instant = int(now().timestamp())
    token = jwt.encode(signer, {"iss": "https://accounts.google.com", "aud": settings.worker_audience, "sub": "local-http-subject",
        "email": settings.task_invoker_email, "email_verified": True, "iat": instant, "exp": instant + 300}).decode()
    headers = {"Authorization": "Bearer " + token}
    before = repo.daily_control()["attempts_reserved"]
    with TestClient(create_app(settings)) as client:
        body = {"run_id": run_id, "generation": retry["generation"]}
        assert client.post("/internal/jobs", json=body).status_code == 401
        assert not made and not repo.run_detail(run_id)["attempts"]
        stale = client.post("/internal/jobs", json={**body, "generation": task["generation"]}, headers=headers)
        assert stale.status_code == 200 and stale.json() == {"status": "STALE"}
        assert not repo.run_detail(run_id)["attempts"]
        response = client.post("/internal/jobs", json=body, headers=headers)
        assert response.status_code == 200 and response.json() == {"status": "TERMINAL", "state": "FAILED"}
        assert response.headers["cache-control"] == "no-store"
        detail = repo.run_detail(run_id)
        assert detail["error_code"] == "AI_NOT_CONNECTED" and all(child["state"] == "FAILED" for child in detail["children"])
        assert len(detail["attempts"]) == 2 * len(case["alerts"])
        assert {step["leg_id"] for step in detail["attempts"]} == {"A1", "A2"}
        assert client.post("/internal/jobs", json=body, headers=headers).json() == {"status": "TERMINAL"}
        assert repo.run_detail(run_id) == detail
    assert repo.get("pipeline_runs", run_id)["lease_claim_count"] == 1
    assert repo.daily_control()["attempts_reserved"] == before


def test_cloud_worker_pins_configuration_and_seals_fault_without_cloud_access(monkeypatch):
    """Synthetic cloud gates with an existing demo client and a refusing SDK double."""
    from dataclasses import replace
    from datetime import timedelta
    from types import SimpleNamespace
    from backend.config import Settings
    from backend.jobs import run_delivery
    from backend.models import DailyControlRequest
    from backend.repository import Repository, now
    repo = Repository(Settings.load())  # Construct only the real loopback demo client.
    repo.settings = replace(repo.settings, mode="cloud", project_id="unit-project", live_ai=True, credits_verified=True,
        credit_verified_until=now() + timedelta(minutes=5), verified_cloud_model_id=repo.settings.model_id,
        verified_cloud_location="global", deployed_code_fingerprint="a" * 64)
    calls = []
    class FaultClient:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        @property
        def models(self): return self
        def count_tokens(self, **_kwargs): return SimpleNamespace(total_tokens=50)
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            failure = RuntimeError("private cloud error must not be stored")
            failure.code = 401
            raise failure
    monkeypatch.setattr("backend.gateway._provider_client", lambda _settings: FaultClient())
    daily = repo.daily_control()
    before = daily["attempts_reserved"]
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=True, limit=12), "operator-demo")
    case = next(item for item in repo.publication()["public_cases"] if len(item["alerts"]) == 1)
    run_id, created = repo.enqueue_triage([item["id"] for item in case["alerts"]], "cloud-fault-fixture")
    assert created
    parent = repo.get("pipeline_runs", run_id)
    bundle = repo.get("config_versions", parent["config_bundle_id"])
    assert bundle["body"]["provider"] == "GOOGLE_CLOUD" and bundle["body"]["location"] == "global"
    assert bundle["body"]["model_id"] == repo.settings.model_id and bundle["body"]["attempts_per_leg"] == 2
    assert {"PROMPT_A2", "PROMPT_A3", "PROMPT_A4", "PROMPT_A5"} <= bundle["component_ids"].keys()
    task = repo.prepare_dispatch(run_id)
    lease = repo.claim_delivery(run_id, task["generation"], "cloud-fault-owner")["lease"]
    run_delivery(repo, lease)
    detail = repo.run_detail(run_id)
    assert detail["state"] == "FAILED" and detail["error_code"] == "PROVIDER_HTTP_401"
    assert len(calls) == 1 and calls[0]["model"] == repo.settings.model_id
    assert {step["leg_id"] for step in detail["attempts"]} == {"A1", "A2"}
    step = next(row for row in detail["attempts"] if row["leg_id"] == "A2")
    stored = repo.get("step_runs", step["id"])
    assert stored["output"] is None and stored["worker_lease"]["owner"] == lease.owner
    assert stored["prompt_version_id"] and stored["context_version_id"] and stored["risk_version_id"]
    assert stored["cost_status"] == "UNKNOWN" and stored["estimated_usd_micros"] is None
    assert "private cloud error" not in str(stored)
    assert repo.daily_control()["attempts_reserved"] == before + 1
    daily = repo.daily_control()
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=False, limit=12), "operator-demo")


def test_source_publisher_resumes_create_only_and_preserves_publication_on_failure():
    """Real isolated demo collections; no cloud client, Auth fixtures or model data."""
    from types import SimpleNamespace
    from uuid import uuid4
    from backend.config import Settings
    from backend.dataset import DATASET_ID, generate_dataset
    from backend.publisher import _prepare_source
    from backend.repository import Conflict, Repository

    repo = Repository(Settings.load())
    client = repo.db
    prefix = "publisher_test_" + uuid4().hex + "_"
    normal = SimpleNamespace(collection=lambda name: client.collection(prefix + name),
        batch=client.batch, transaction=client.transaction)
    repo.db = normal
    previous = repo.publish([], {"note": "Isolated deterministic publication fixture"}, "publisher-test")
    calls = []

    class InterruptedBatch:
        def __init__(self): self.batch = client.batch()
        def create(self, *args, **kwargs): self.batch.create(*args, **kwargs)
        def commit(self, **kwargs):
            calls.append(True)
            if len(calls) == 2: raise RuntimeError("Local test interruption before commit")
            return self.batch.commit(**kwargs)

    repo.db = SimpleNamespace(collection=normal.collection, batch=InterruptedBatch, transaction=normal.transaction)
    data = generate_dataset()
    with pytest.raises(RuntimeError, match="Local test interruption"):
        _prepare_source(repo, data, "publisher-test")
    repo.db = normal
    assert repo.get("datasets", DATASET_ID)["state"] == "SEEDING"
    assert repo.publication()["id"] == previous
    customer_id = next(iter(data.customers))
    original = repo.get("customers", customer_id)
    assert original
    ref = normal.collection("customers").document(customer_id)
    ref.update({"display_name": "Corrupted test-only source"})
    with pytest.raises(Conflict, match="EXISTING_SOURCE_MISMATCH"):
        _prepare_source(repo, data, "publisher-test")
    assert repo.publication()["id"] == previous
    ref.update({"display_name": original["display_name"]})
    published = _prepare_source(repo, data, "publisher-test")
    assert published != previous and repo.publication()["source_provenance"] == "DETERMINISTIC_ONLY"
    assert len(repo.publication()["public_cases"]) == 12
    frozen = repo.get("datasets", DATASET_ID)
    assert frozen["state"] == "READY" and frozen["manifest_hash"] == data.manifest_hash
    assert repo.get("customers", customer_id) == original
    alert_id = next(iter(repo.list("alerts")))["id"]
    normal.collection("alerts").document(alert_id).update({"status": "ERROR", "latest_run_id": "test-unfinished-work"})
    mutable_alert = repo.get("alerts", alert_id)
    config_before = {doc.id: doc.to_dict() for doc in normal.collection("config_versions").stream()}
    assert _prepare_source(repo, data, "publisher-test") == published
    assert repo.get("datasets", DATASET_ID) == frozen and repo.get("alerts", alert_id) == mutable_alert
    assert {doc.id: doc.to_dict() for doc in normal.collection("config_versions").stream()} == config_before
    config_id = next(iter(config_before))
    normal.collection("config_versions").document(config_id).update({"body": {"tampered": True}})
    with pytest.raises(Conflict, match="EXISTING_CONFIGURATION_MISMATCH"):
        _prepare_source(repo, data, "publisher-test")
    assert repo.publication()["id"] == published
    assert not repo.list("step_runs") and not repo.list("feedback_events")


def test_operator_policy_queue_and_transactional_application_rollback(monkeypatch):
    """Isolated policy mechanics; the eligible-evidence double is NOT a model result."""
    from types import SimpleNamespace
    from uuid import uuid4
    from backend.config import Settings
    from backend.dataset import DATASET_ID
    from backend.models import PolicyChangeRequest, FeedbackRequest
    from backend.repository import Conflict, Repository
    repo = Repository(Settings.load())
    publication = repo.publication()
    source_cases = repo.list("cases")
    client = repo.db
    prefix = "policy_mechanics_test_" + uuid4().hex + "_"
    repo.db = SimpleNamespace(collection=lambda name: client.collection(prefix + name), transaction=client.transaction)
    repo.create("publications", "test-only", publication)
    for source_case in source_cases: repo.create("cases", source_case["id"], source_case)
    repo.db.collection("publications").document("active").set({"publication_id": "test-only"})
    for case in publication["public_cases"]:
        for alert in case["alerts"]: repo.create("alerts", alert["id"], alert)
    case = next(row for row in publication["public_cases"] if len(row["alerts"]) >= 2)
    frozen_id, remaining = case["alerts"][0]["id"], [row["id"] for row in case["alerts"][1:]]
    repo.db.collection("alerts").document(frozen_id).update({"feedback_revision": 1, "status": "COMPLETE"})
    queue = repo.operator_queue()
    assert queue["policy_version_id"] == "detector-v1"
    assert next(row for row in queue["cases"] if row["id"] == case["id"])["progress"]["frozen"] == 1
    with pytest.raises(Conflict, match="frozen"):
        repo.save_feedback(frozen_id, FeedbackRequest(verdict="INCONCLUSIVE", notes="Refusal fixture", expected_revision=1), "test-only")
    with pytest.raises(Conflict, match="actionable"):
        repo.enqueue_triage([frozen_id, *remaining], "test-only", "detector-v1")
    parent, created = repo.enqueue_triage(remaining, "test-only", "detector-v1")
    assert created and len(repo.get("pipeline_runs", parent)["child_run_ids"]) == len(remaining)
    assert repo.get("alerts", frozen_id)["feedback_revision"] == 1
    ident = uuid4().hex[:24]
    repo.create("recommendations", ident, {"dataset_id": DATASET_ID, "state": "APPROVED", "revision": 0})
    request = PolicyChangeRequest(expected_revision=0, expected_policy_revision=0, notes="Test-only policy transaction")
    with pytest.raises(Conflict, match="genuine"):
        repo.apply_recommendation(ident, request, "test-only")
    assert repo.active_policy()["revision"] == 0
    # Verify atomic policy mechanics independently of genuine AI/evaluation eligibility.
    monkeypatch.setattr(repo, "application_evidence", lambda *_args: {"candidate": {"id": "hv-20000", "kind": "RULE_THRESHOLD", "threshold_aud_minor": 2000000},
        "simulation_id": "test-only-not-genuine", "candidate_hash": "test-only-not-genuine"})
    before_publication = repo.publication()
    applied = repo.apply_recommendation(ident, request, "test-only")
    assert applied["state"] == "APPLIED" and repo.active_policy()["revision"] == 1
    assert repo.publication() == before_publication
    assert repo.get("alerts", frozen_id)["feedback_revision"] == 1
    bundle = repo.get("config_versions", repo.ensure_baseline())
    assert bundle["body"]["detector_version"] == applied["applied_policy_id"]
    with pytest.raises(Conflict, match="changed"):
        repo.apply_recommendation(ident, request, "test-only")
    with pytest.raises(Conflict, match="Policy changed"):
        repo.enqueue_triage(remaining, "test-only", "detector-v1")
    rolled = repo.apply_recommendation(ident, PolicyChangeRequest(expected_revision=1, expected_policy_revision=1,
        notes="Test-only rollback"), "test-only", rollback=True)
    assert rolled["state"] == "ROLLED_BACK" and repo.active_policy()["policy_version_id"] == "detector-v1"
    assert repo.active_policy()["revision"] == 2 and repo.get("config_versions", applied["applied_policy_id"])
    assert not repo.list("step_runs") and not repo.list("feedback_events")

    # Isolate the save transaction mechanics from AI provenance validation.
    # These TEST_ONLY records are not genuine analyst/model evidence.
    from concurrent.futures import ThreadPoolExecutor
    completed = "test-only-completed-run"
    repo.create("pipeline_runs", completed, {"id": completed, "dataset_id": DATASET_ID, "state": "COMPLETE",
        "alert_id": remaining[0], "case_id": case["id"], "config_bundle_id": repo.ensure_baseline()})
    repo.db.collection("alerts").document(remaining[0]).update({"status": "COMPLETE", "current_run_id": completed})
    monkeypatch.setattr(repo, "_sealed_chain", lambda *_args: [])
    feedback = FeedbackRequest(verdict="INCONCLUSIVE", notes="TEST_ONLY transaction fixture", expected_revision=0)
    def save(_index):
        try: return repo.save_feedback(remaining[0], feedback, "TEST_ONLY")
        except Conflict: return None
    with ThreadPoolExecutor(max_workers=2) as pool: saved = list(pool.map(save, range(2)))
    assert sum(row is not None for row in saved) == 1
    assert len(repo.list("feedback_events")) == 1 and not repo.list("step_runs")
    with pytest.raises(Conflict, match="frozen"):
        repo.save_feedback(remaining[0], feedback.model_copy(update={"expected_revision": 1}), "TEST_ONLY")


def test_local_reservations_follow_admin_limit_above_twelve(monkeypatch):
    """Real isolated ledger; no provider calls or successful model output."""
    from dataclasses import replace
    from datetime import timedelta
    from types import SimpleNamespace
    from uuid import uuid4
    from backend.config import Settings
    from backend.dataset import DATASET_ID, content_hash, stable_id
    from backend.models import DailyControlRequest, PipelineRun, StepRun
    from backend.repository import Conflict, Repository, now

    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-credential")
    repo = Repository(replace(Settings.load(), local_gemini_enabled=True, local_gemini_free_verified=True,
        local_gemini_verified_until=now() + timedelta(minutes=5)))
    client = repo.db
    prefix = "local_limit_test_" + uuid4().hex + "_"
    repo.db = SimpleNamespace(collection=lambda name: client.collection(prefix + name), transaction=client.transaction)
    bundle_id = repo.ensure_baseline()
    assert repo.get("config_versions", bundle_id)["body"]["max_daily_attempts"] == 120
    daily = repo.daily_control()
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=True, limit=13), "test-only")
    for index in range(14):
        run_id = uuid4().hex
        repo.create("pipeline_runs", run_id, PipelineRun(id=run_id, dataset_id=DATASET_ID,
            kind="TRIAGE_ALERT", config_bundle_id=bundle_id, actor_uid="test-only", state="RUNNING").model_dump())
        request = _reservation_input(repo, bundle_id, "A2", "test-only")
        step = StepRun(id=stable_id(run_id, "A2", 1), dataset_id=DATASET_ID, run_id=run_id,
            leg_id="A2", config_bundle_id=bundle_id, state="STARTED", model_id=repo.settings.active_model_id,
            started_at=now(), input_hash=content_hash(request), input_snapshot=request,
            usage_status="UNKNOWN", cost_status="UNKNOWN")
        if index < 13:
            assert repo.reserve_model_attempt(step)
        else:
            with pytest.raises(Conflict, match="CAP_REACHED"):
                repo.reserve_model_attempt(step)
            assert repo.get("step_runs", step.id) is None
    assert repo.daily_control()["attempts_reserved"] == 13


def test_frozen_rate_card_reservation_and_failed_output_accounting(monkeypatch):
    """Isolated real demo ledger plus invalid JSON; no successful model fixture."""
    from dataclasses import replace
    from datetime import timedelta
    from types import SimpleNamespace
    from uuid import uuid4
    from backend.config import Settings
    from backend.dataset import DATASET_ID, stable_id
    from backend.gateway import generate_json
    from backend.gemini_smoke import SmokeReply
    from backend.models import DailyControlRequest, PipelineRun, StepRun
    from backend.repository import Conflict, Repository, now
    from test_pricing import card_fixture

    _body, settings, instant = card_fixture()
    repo = Repository(Settings.load())  # The only actual client remains loopback.
    client = repo.db
    prefix = "pricing_test_" + uuid4().hex + "_"
    repo.db = SimpleNamespace(collection=lambda name: client.collection(prefix + name), transaction=client.transaction)
    repo.settings = replace(settings, project_id="unit-project", live_ai=True, credits_verified=True,
        credit_verified_until=now() + timedelta(minutes=5), verified_cloud_model_id=settings.model_id,
        deployed_code_fingerprint="a" * 64)
    bundle_id = repo.ensure_baseline()
    bundle = repo.get("config_versions", bundle_id)
    card_id = bundle["component_ids"]["RATE_CARD"]
    frozen = repo.get("config_versions", card_id)
    assert repo.ensure_baseline() == bundle_id and repo.get("config_versions", card_id) == frozen
    parent_id, child_id = uuid4().hex, uuid4().hex
    repo.create("pipeline_runs", parent_id, PipelineRun(id=parent_id, dataset_id=DATASET_ID,
        kind="TRIAGE_BATCH", case_id="test-only-case", config_bundle_id=bundle_id,
        actor_uid="test-only", child_run_ids=[child_id]).model_dump())
    repo.create("pipeline_runs", child_id, PipelineRun(id=child_id, dataset_id=DATASET_ID,
        kind="TRIAGE_ALERT", case_id="test-only-case", alert_id="test-only-alert", config_bundle_id=bundle_id,
        parent_run_id=parent_id, actor_uid="test-only", state="RUNNING").model_dump())
    dispatch = repo.prepare_dispatch(parent_id)
    lease = repo.claim_delivery(parent_id, dispatch["generation"], "test-only-owner")["lease"]
    daily = repo.daily_control()
    repo.update_daily_control(DailyControlRequest(expected_revision=daily["revision"], live_enabled=True, limit=12), "test-only")
    from backend.dataset import content_hash
    request = _reservation_input(repo, bundle_id, "A2", "test-only")
    profile = bundle["body"]["generation_profiles"]["A2"]
    step = StepRun(id=stable_id(child_id, "A2", 1), dataset_id=DATASET_ID, run_id=child_id,
        leg_id="A2", alert_id="test-only-alert", case_id="test-only-case", config_bundle_id=bundle_id,
        state="STARTED", model_id=settings.model_id, started_at=instant, input_hash=content_hash(request), input_snapshot=request,
        usage_status="UNKNOWN", cost_status="UNKNOWN", worker_lease=lease)
    repo.settings = replace(repo.settings, deployed_code_fingerprint="b" * 64)
    with pytest.raises(Conflict, match="CONFIG_SOURCE_MISMATCH"):
        repo.reserve_model_attempt(step.model_copy(update={"rate_card_id": card_id}))
    repo.settings = replace(repo.settings, deployed_code_fingerprint="a" * 64)
    with pytest.raises(Conflict, match="CONFIG_RATE_CARD_MISMATCH"):
        repo.reserve_model_attempt(step)
    assert repo.daily_control()["attempts_reserved"] == 0 and not repo.get("step_runs", step.id)
    class FaultClient:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        @property
        def models(self): return self
        def count_tokens(self, **_kwargs): return SimpleNamespace(total_tokens=100)
        def generate_content(self, **kwargs):
            assert kwargs["config"]["service_tier"] == "standard"
            return SimpleNamespace(text="invalid-test-json", response_id="test-only", usage_metadata=SimpleNamespace(
                prompt_token_count=100, cached_content_token_count=20, candidates_token_count=10,
                thoughts_token_count=5, tool_use_prompt_token_count=0, total_token_count=115, service_tier="standard"))
    monkeypatch.setattr("backend.gateway._provider_client", lambda _settings: FaultClient())
    result = generate_json(repo, step, "Invalid JSON test", SmokeReply, input_limit=512,
        output_limit=profile["max_output_tokens"], evidence={}, thinking_level=profile["thinking_level"], temperature=profile["temperature"])
    assert result.error_code == "OUTPUT_INVALID"
    stored = repo.get("step_runs", step.id)
    assert stored["state"] == "FAILED" and stored["output"] is None
    assert stored["rate_card_id"] == card_id and stored["estimated_usd_micros"] == 115
    assert repo.daily_control()["attempts_reserved"] == 1
    assert repo.reserve_model_attempt(step.model_copy(update={"rate_card_id": card_id})) is False
    assert repo.get("config_versions", card_id) == frozen
