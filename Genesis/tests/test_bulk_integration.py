"""Isolated Firestore transactions only. No provider outputs or human verdicts."""
import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
import pytest
from backend.bulk_dataset import corpus, ID
from backend.bulk_api import Start
from backend import bulk_jobs, bulk_learning
from backend.config import Settings
from backend.repository import Repository, Conflict

pytestmark = pytest.mark.skipif(os.getenv('FIRESTORE_EMULATOR_HOST') != '127.0.0.1:18081', reason='Use isolated Firebase integration endpoints')


def test_baseline_split_is_frozen_disjoint_and_cannot_claim_ai_reviews(repo):
    from backend import seeded_baseline as baseline
    from backend.bulk_dataset import SEEDED_ID
    from backend.dataset import content_hash, stable_id
    training, reserved = baseline.selection()
    scoped = Repository(repo.settings, SEEDED_ID); scoped.db = repo.db
    rows = training + reserved
    for start in range(0, len(rows), 400):
        batch = repo.db.batch()
        for row in rows[start:start + 400]:
            body = {'case_id': row['id'], 'provenance': 'ISOLATED_TEST_FIXTURE_NOT_REAL_EVIDENCE'}
            batch.create(repo.db.collection('seeded_case_history').document(stable_id(SEEDED_ID, row['id'])),
                {'dataset_id': SEEDED_ID, 'case_id': row['id'], 'body': body, 'content_hash': content_hash(body)})
        batch.commit()
    first = baseline.prepare(scoped)
    assert baseline.prepare(scoped)['baseline_id'] == first['baseline_id']
    assert baseline.active(scoped)['id'] == first['baseline_id']
    status = baseline.progress(scoped)
    assert status['total_cases'] == 3000 and status['pending_ai_reviews'] == 2000
    assert status['reserved_cases'] == 1000 and status['ai_reviewed_cases'] == status['human_reviews'] == 0
    assert not scoped.list('step_runs') and not scoped.list('feedback_events')
    chunk = first['chunks'][0]['id']
    repo.db.collection('seeded_baseline_chunks').document(chunk).update({'body.scope': 'RESERVED'})
    with pytest.raises(Conflict): baseline.active(scoped)


def test_seeded_reference_import_and_refused_actual_run_preserve_operational_state(repo, monkeypatch):
    from itertools import islice
    from backend import seeded_history as seeded
    from backend.bulk_dataset import SEEDED_ID
    from backend.jobs import run_local
    from backend.calibration import active_label_policy
    sample = dict(islice(seeded.catalog().items(), 3))
    monkeypatch.setattr(seeded, 'catalog', lambda: sample)
    scoped = Repository(repo.settings, SEEDED_ID); scoped.db = repo.db
    before = active_label_policy(repo)
    result = seeded.prepare(scoped, 'TEST_ONLY_reference_import')
    assert result['created'] == result['cases'] == 3 and result['model_calls'] == 0
    assert seeded.prepare(scoped, 'TEST_ONLY_reference_import')['created'] == 0
    records = scoped.list('seeded_case_history')
    assert len(records) == 3 and all(not row['body']['human_review'] for row in records)
    assert not repo.list('feedback_events', ID)
    worker = seeded.SeededRepository(repo.settings, next(iter(sample))); worker.db = repo.db
    alerts = worker.materialize()
    parent, created = worker.enqueue_triage([row['id'] for row in alerts], 'TEST_ONLY', 'detector-v1', 'auto-label-v1')
    assert created and run_local(worker, parent)
    detail = worker.run_detail(parent)
    assert detail['state'] == 'FAILED' and detail['error_code'] == 'AI_NOT_CONNECTED'
    assert not any(row.get('execution_provenance') == 'REAL_PROVIDER' for row in detail['attempts'])
    assert not repo.list('bulk_case_progress', ID) and not repo.list('feedback_events', SEEDED_ID)
    assert active_label_policy(repo) == before
    status = seeded.summary(scoped)
    assert status['reference_cases'] == status['pending_ai_cases'] == 3
    assert status['completed_ai_cases'] == status['genuine_human_reviews'] == 0
    assert status['examples'][0]['briefs'] == []
    comparison = seeded.evaluate(scoped, 'TEST_ONLY')
    assert comparison['body']['counts']['alerts'] == 0
    assert comparison['body']['observation_chunks'] == []
    assert seeded.evaluate(scoped, 'TEST_ONLY')['id'] == comparison['id']


@pytest.fixture
def repo(monkeypatch):
    original = Repository(Settings.load()); client = original.db; prefix = 'bulk_TEST_ONLY_' + uuid4().hex + '_'
    db = SimpleNamespace(collection=lambda name: client.collection(prefix + name), transaction=client.transaction,
        get_all=client.get_all, batch=client.batch)
    original.db = db
    init = bulk_jobs.BulkRepository.__init__
    def scoped(self, *args):
        init(self, *args); self.db = db
    monkeypatch.setattr(bulk_jobs.BulkRepository, '__init__', scoped)
    return original


def test_durable_duplicate_start_capacity_pause_and_frozen_source(repo):
    ids = [r['id'] for r in corpus().page(limit=100)['items'] if r['rules']][:2]
    before = repo.get('policy_controls', ID)
    plan = bulk_jobs.preview(repo, ids, ID, 'test-operator')
    request = Start(case_ids=ids, dataset_id=ID, selection_hash=plan['selection_hash'], idempotency_key='test-duplicate-start')
    with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(lambda _: bulk_jobs.create(repo, request, 'test-operator'), range(2)))
    assert results[0]['id'] == results[1]['id'] and results[0]['counts']['PENDING'] == 2
    job = bulk_jobs.advance(repo, results[0]['id'])
    assert job['state'] == 'PAUSED_CAPACITY' and not any(m['parent_id'] for m in job['members'])
    with pytest.raises(Conflict): bulk_jobs.decision(repo, job['id'], 0, 'cancel', 'test-operator')
    cancelled = bulk_jobs.decision(repo, job['id'], job['revision'], 'cancel', 'test-operator')
    assert cancelled['state'] == 'CANCELLED' and repo.get('policy_controls', ID) == before
    assert not repo.list('pipeline_runs', ID) and not repo.list('step_runs', ID)


def test_synthetic_freeze_validation_once_never_updates_operational_controls(repo):
    original = repo.get('auto_label_controls', 'synthetic-v1-20261015')
    frozen = bulk_learning.prepare(repo, 'test-operator')
    assert bulk_learning.prepare(repo, 'test-operator')['id'] == frozen['id']
    repo.create(bulk_learning.COLLECTION, 'zz_TEST_ONLY_cursor', {'body': {'dataset_id': ID}})
    page = repo.page(bulk_learning.COLLECTION, 1, filters=[('body.dataset_id', ID)])
    assert page['next_cursor'] == frozen['id']
    assert repo.page(bulk_learning.COLLECTION, 1, page['next_cursor'], [('body.dataset_id', ID)])['items'][0]['id'] == 'zz_TEST_ONLY_cursor'
    assert not any(item['candidate'] for item in frozen['body']['results'])
    with pytest.raises(Conflict, match='No candidate to validate'): bulk_learning.act(repo, frozen['id'], 'validate', 0, 'test-operator')
    assert repo.get('synthetic_validation_controls', ID) is None
    with pytest.raises(Conflict): bulk_learning.act(repo, frozen['id'], 'approve', 0, 'test-operator')
    with pytest.raises(Conflict): bulk_learning.act(repo, frozen['id'], 'apply', 0, 'test-operator')
    assert repo.get('auto_label_controls', 'synthetic-v1-20261015') == original
    assert not repo.list('feedback_events', ID) and not repo.list('step_runs', ID)


def test_controlled_exercise_uses_real_calibration_and_isolated_approval_application(repo):
    from backend import cutoff_exercise as exercise
    before = {name: repo.get(name, ID) for name in ('synthetic_controls', 'auto_label_controls', 'policy_controls')}
    assert exercise.state(repo)['record'] is None
    current = exercise.act(repo, 'prepare', 0, 'test-operator')['record']
    original_id = current['id']
    assert current['body']['dataset_id'] == exercise.ID
    target = next(r for r in current['body']['results'] if r['rule_id'] == 'HIGH_VALUE')
    assert target['candidate']['thresholds']['fp'] == .4
    with pytest.raises(Conflict): exercise.act(repo, 'approve', current['revision'], 'test-operator')
    for action in ('validate', 'approve', 'apply', 'test'):
        current = exercise.act(repo, action, current['revision'], 'test-operator')['record']
    result = current['comparison']
    assert result['cases'] == 100 and result['provider_calls'] == 0
    assert result['before'] == {'AUTO_TP':50,'AUTO_FP':25,'AUTO_UNCERTAIN':25}
    assert result['after'] == {'AUTO_TP':50,'AUTO_FP':50,'AUTO_UNCERTAIN':0}
    assert result['applied_errors']['wrong_fp'] == result['applied_errors']['wrong_tp'] == 0
    assert exercise.act(repo, 'test', current['revision'], 'test-operator')['record']['comparison'] == result
    assert exercise.act(repo, 'prepare', 0, 'test-operator')['record']['id'] == original_id
    with pytest.raises(Conflict): exercise.act(repo, 'test', 0, 'test-operator')
    assert {name: repo.get(name, ID) for name in before} == before
    assert not repo.list('feedback_events', ID) and not repo.list('step_runs', ID)
    exercise_repo = exercise.scoped(repo)
    assert exercise_repo.get('synthetic_validation_controls', exercise.ID)['calibration_id'] == original_id


def test_member_parent_link_survives_completion_and_repeated_enqueue(repo):
    row = next(r for r in corpus().page(limit=100)['items'] if r['rules'])
    plan = bulk_jobs.preview(repo, [row['id']], ID, 'test-operator')
    request = Start(case_ids=[row['id']], dataset_id=ID, selection_hash=plan['selection_hash'], idempotency_key='test-checkpoint-link')
    job = bulk_jobs.create(repo, request, 'test-operator'); member = job['members'][0]
    worker, case = bulk_jobs.source(repo, row['id'], ID)
    parent, created = worker.enqueue_triage(member['alert_ids'], 'test-operator', plan['detector_policy'], plan['auto_label_policy'], bulk_member=member['id'])
    assert created
    # A terminal refusal is real ledger behavior; no successful provider output is faked.
    from backend.jobs import run_local
    assert run_local(worker, parent)
    assert worker.get('pipeline_runs', parent)['state'] == 'FAILED'
    repeat, created = worker.enqueue_triage(member['alert_ids'], 'test-operator', plan['detector_policy'], plan['auto_label_policy'], bulk_member=member['id'])
    assert repeat == parent and not created
    assert len(worker.list('pipeline_runs', ID)) == 1 + len(member['alert_ids'])
    assert all(step['execution_provenance'] in {'DETERMINISTIC', 'NOT_SENT'} for step in worker.list('step_runs'))


def test_full_native_status_queue_import_is_idempotent_and_filters_are_paged(repo):
    assert bulk_jobs.import_progress(repo) == 20000
    assert bulk_jobs.import_progress(repo) == 0
    first = bulk_jobs.queue(repo, limit=50, customer_type='INDIVIDUAL', rule='HIGH_VALUE', status='awaiting_triage')
    second = bulk_jobs.queue(repo, limit=50, cursor=first['next_cursor'], customer_type='INDIVIDUAL', rule='HIGH_VALUE', status='awaiting_triage')
    assert first['total'] == second['total'] > 100
    assert not {r['id'] for r in first['items']} & {r['id'] for r in second['items']}
    assert all(r['customer_type'] == 'INDIVIDUAL' and 'HIGH_VALUE' in r['rules'] and not r['triaged'] for r in first['items'])
    assert bulk_jobs.queue(repo, status='frozen')['total'] == 0
    assert bulk_jobs.queue(repo, query='not a fictional name')['total'] == 0


def test_corpus_evolution_private_reads_scope_limits_and_no_automatic_work(repo, monkeypatch):
    from fastapi.testclient import TestClient
    from backend import api
    monkeypatch.setattr(api, 'Repository', lambda _settings, *_scope: repo)
    def claims(token, **_kwargs):
        if token == 'invalid': raise ValueError('TEST_ONLY invalid token')
        return {'uid': 'operator-demo' if token == 'operator' else 'outside-allowlist'}
    monkeypatch.setattr(api.auth, 'verify_id_token', claims)
    client = TestClient(api.create_app())
    base = '/api/operator/bulk/evolution'
    reads = ['/review-summary', '/rule-matrix', '/snapshots', '/patterns', '/trends', '/observations', '/auto-label/candidates', '/auto-label/calibrations', '/auto-label/assessments', '/public-brief']
    for suffix in reads:
        assert client.get(base + suffix).status_code == 401
        assert client.get(base + suffix, headers={'Authorization': 'Bearer invalid'}).status_code == 401
        assert client.get(base + suffix, headers={'Authorization': 'Bearer outsider'}).status_code == 403
        result = client.get(base + suffix, headers={'Authorization': 'Bearer operator'})
        assert result.status_code == 200, result.text
        assert result.headers['cache-control'] == 'no-store'
    summary = client.get(base + '/review-summary', headers={'Authorization': 'Bearer operator'}).json()
    assert summary['total_cases'] == 40000 and summary['operational_cases'] == 20000
    assert summary['reviewed_alerts'] == summary['compared'] == 0
    assert len(client.get(base + '/rule-matrix', headers={'Authorization': 'Bearer operator'}).json()['rules']) == 9
    assert client.get(base + '/auto-label/candidates?limit=101', headers={'Authorization': 'Bearer operator'}).status_code == 422
    assert client.get('/api/demo/bulk/evolution/brief').json()['publication'] is None
    headers = {'Authorization': 'Bearer operator'}
    for scope in ('corpus',):
        for resource in ('usage', 'runs', 'audit'):
            assert client.get(f'/api/operator/{resource}?scope={scope}', headers=headers).status_code == 200
    from backend.dataset import DATASET_ID
    from backend.repository import now
    for ident, dataset in [('corpus-audit', ID), ('archive-audit', DATASET_ID)]:
        repo.create('audit_events', ident, {'dataset_id': dataset, 'action': 'TEST_ONLY', 'occurred_at': now()})
    assert [row['id'] for row in client.get('/api/operator/audit?scope=corpus', headers=headers).json()['items']] == ['corpus-audit']
    assert client.get('/api/operator/audit?scope=archive', headers=headers).status_code == 422
    assert client.get('/api/operator/usage?scope=unknown', headers=headers).status_code == 422
    assert not repo.list('pipeline_runs', ID) and not repo.list('feedback_events', ID) and not repo.list('auto_label_candidates', ID)
