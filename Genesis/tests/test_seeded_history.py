from copy import deepcopy
from types import SimpleNamespace
import pytest

from backend.bulk_dataset import ID, SEEDED_ID, corpus
from backend import seeded_history as seeded
from backend.repository import Conflict
from backend.dataset import content_hash, stable_id


def test_seeded_history_is_explicit_reference_evidence_without_forged_humans():
    row = next(iter(seeded.catalog().values()))
    record = seeded.history_record(row)
    assert record['dataset_id'] == SEEDED_ID != ID
    assert record['body']['source_dataset_id'] == ID
    assert not record['body']['human_review']
    assert record['body']['provenance'] == seeded.PROVENANCE
    assert record['body']['ai_investigation'] == 'NOT_RUN'
    assert record['body']['python_risk'] == corpus().case(row['id'])['risk']
    assert record['body']['deterministic_provenance'] == 'PYTHON_COMPUTED'
    assert record['content_hash'] == content_hash(record['body'])
    assert seeded.history_record(deepcopy(row)) == record


def test_seeded_investigations_reject_operational_and_reserved_cases_and_human_feedback():
    with corpus().connect() as db:
        reserved = db.execute("SELECT id FROM cases WHERE partition='VALIDATION' LIMIT 1").fetchone()[0]
        operational = db.execute("SELECT id FROM cases WHERE partition='PENDING' LIMIT 1").fetchone()[0]
    for case_id in [reserved, operational, 'missing']:
        with pytest.raises(LookupError): seeded.SeededRepository(None, case_id)
    worker = object.__new__(seeded.SeededRepository)
    with pytest.raises(Conflict, match='simulated'): worker.save_feedback('anything', None, 'operator-demo')


def test_seeded_actual_model_inputs_exclude_reference_verdicts_and_have_distinct_alert_ids(monkeypatch):
    row = next(iter(seeded.catalog().values()))
    worker = object.__new__(seeded.SeededRepository)
    worker.case_id = row['id']
    data = worker.load_dataset()
    from backend.engine import enrich, detect, risk_assessment
    evidence = enrich(data, data.cases[row['id']])
    assert 'reference_verdict' not in evidence and 'reference_prediction' not in evidence
    assert data.id == SEEDED_ID
    source = corpus().case(row['id'])
    actual = detect(data, data.cases[row['id']])
    assert {a['id'] for a in actual}.isdisjoint(a['id'] for a in source['alerts'])
    assert risk_assessment(evidence) == source['risk']


def test_seeded_worker_requires_local_authorization_before_writes():
    repo = SimpleNamespace(settings=SimpleNamespace(mode='cloud'))
    with pytest.raises(Conflict): seeded.run_pending(repo, 'test-only')


def test_reference_comparison_denominators_preserve_uncertainty_and_identity_counts():
    rows = [dict(case_id='case-1', identity_id='identity-1', reference_verdict='TRUE_POSITIVE', predicted_verdict='AUTO_TP'),
        dict(case_id='case-1', identity_id='identity-1', reference_verdict='FALSE_POSITIVE', predicted_verdict='AUTO_TP'),
        dict(case_id='case-2', identity_id='identity-2', reference_verdict='FALSE_POSITIVE', predicted_verdict='AUTO_UNCERTAIN'),
        dict(case_id='case-3', identity_id='identity-3', reference_verdict='INCONCLUSIVE', predicted_verdict='AUTO_FP')]
    assert seeded.comparison_counts(rows) == dict(alerts=4, cases=3, identities=3, comparable=2, agreed=1, uncertain=1, reference_inconclusive=1)


def test_explicit_free_model_selection_preserves_gates_and_forbids_fallback(monkeypatch):
    from dataclasses import replace
    from datetime import timedelta
    from backend.config import Settings
    from backend.repository import now
    monkeypatch.setenv('GEMINI_API_KEY', 'TEST_ONLY_never_sent')
    settings = replace(Settings.load(), local_gemini_enabled=True, local_gemini_free_verified=True,
        local_gemini_verified_until=now() + timedelta(minutes=5), local_gemini_model='gemini-3-flash-preview')
    assert settings.ai_authorized() and settings.is_model_authorized('gemini-3-flash-preview')
    assert not settings.is_model_authorized('gemini-3.5-flash-lite')
    assert not replace(settings, local_gemini_free_verified=False).ai_authorized()
    assert not replace(settings, local_gemini_model='unverified-model').ai_authorized()
    assert set(settings.agent_profiles.leg_model_map.values()) == {'gemini-3-flash-preview'}


def test_local_pacing_spaces_http_before_reservation_without_real_wait(monkeypatch):
    from backend import gateway
    clock = [10.0]; waits = []
    monkeypatch.setenv('LOCAL_GEMINI_MIN_INTERVAL_SECONDS', '5')
    monkeypatch.setattr(gateway, '_last_local_http_at', None)
    monkeypatch.setattr(gateway, 'monotonic', lambda: clock[0])
    def wait(seconds):
        waits.append(seconds); clock[0] += seconds
    monkeypatch.setattr(gateway, 'sleep', wait)
    gateway._pace_local(SimpleNamespace(mode='local'))
    clock[0] += 2
    gateway._pace_local(SimpleNamespace(mode='local'))
    assert waits == [3] and clock[0] == 15
    gateway._pace_local(SimpleNamespace(mode='cloud'))
    assert waits == [3]
