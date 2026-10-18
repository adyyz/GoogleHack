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
            body = {'case_id': row['id'], 'provenance': 'ISOLATED_TEST_FIXTURE_NOT_REAL_EVIDENCE',
                'identity_id': row['identity_id'], 'name': row['name'], 'rules': row['rules'],
                'reference_heuristic_score': row['reference_score'], 'reference_verdict': row['reference_verdict'],
                'reference_prediction': row['reference_prediction'], 'python_risk': {'tier': row['risk_tier']},
                'protected_signals': ['TEST_ONLY'] if row['requires_review'] else [], 'missing_context': []}
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
    from scripts.import_agent_drafts import import_drafts
    imported = import_drafts(scoped, apply=True, allow_equivalent_baseline=True)
    assert imported['created'] == imported['agent_drafted'] == 2000
    assert imported['gemini'] == imported['pending'] == 0
    assert import_drafts(scoped, apply=True, allow_equivalent_baseline=True)['created'] == 0
    assert not scoped.list('step_runs') and not scoped.list('feedback_events')
    assert baseline.progress(scoped)['agent_draft_reviewed_cases'] == 2000
    from backend import baseline_workspace as workspace
    assert workspace.prepare(scoped)['created'] == 0
    assert workspace.prepare(scoped, apply=True)['created'] == 9
    assert workspace.prepare(scoped, apply=True)['created'] == 0
    active = workspace.view(scoped)
    assert active['cases'] == 3000 and active['identities'] == 200
    summary = workspace.summary(workspace.analytics(scoped), active)
    assert summary['cases'] == 3000 and summary['reference_annotations'] == 2000 and summary['initially_unprocessed'] == 1000
    assert summary['advisory']['agent_draft_reviewed_cases'] == 2000 and summary['advisory']['pending_ai_reviews'] == 0
    first_page = workspace.queue(scoped, limit=50)
    second_page = workspace.queue(scoped, limit=50, cursor=first_page['next_cursor'])
    assert first_page['total'] == second_page['total'] == 3000
    assert not {row['id'] for row in first_page['items']} & {row['id'] for row in second_page['items']}
    assert workspace.queue(scoped, status='reference')['total'] == 2000
    reserved_page = workspace.queue(scoped, status='awaiting_triage')
    assert reserved_page['total'] == 1000
    assert all(not any(key.startswith('reference_') for key in row) for row in reserved_page['items'])
    filtered = workspace.queue(scoped, identity=rows[0]['identity_id'], customer_type=rows[0]['customer_type'], rule=rows[0]['rules'][0])
    assert filtered['items'] and all(row['identity_id'] == rows[0]['identity_id'] for row in filtered['items'])
    assert workspace.queue(scoped, query='not a fictional name')['total'] == 0
    assert workspace.queue(scoped, status='awaiting_review', private=True)['total'] == 0
    from backend.rule_intelligence import matrix
    analytics = workspace.analytics(scoped)
    assert analytics.review_statistics()['reviewed_alerts'] == 0
    report = matrix(analytics)
    assert len(report['rules']) == 9 and sum(row['alert_count'] for row in report['rules']) == sum(summary['rule_alerts'].values())
    assert workspace.reference_summary(scoped)['cases'] == 2000
    draft_ref = scoped.db.collection('seeded_advisory_reviews').document(stable_id(first['baseline_id'], training[0]['id']))
    original_draft = draft_ref.get().to_dict()
    draft_ref.delete()
    refreshed = workspace.summary(analytics, active)['advisory']
    assert refreshed['agent_draft_reviewed_cases'] == 1999 and refreshed['pending_ai_reviews'] == 1
    draft_ref.create(original_draft)
    assert workspace.summary(analytics, active)['advisory']['pending_ai_reviews'] == 0
    from backend import projected_reviews
    projected = projected_reviews.prepare(scoped, apply=True)
    assert projected['created'] == 2000 and projected['assignment_counts'] == {'AGREE': 1500, 'DISAGREE': 400, 'UNCERTAIN': 100}
    assert projected_reviews.prepare(scoped, apply=True)['created'] == 0
    aggregate = projected_reviews.summary(scoped)
    assert aggregate['prepared'] and aggregate['cases'] == 2000 and len(aggregate['rules']) == 9
    assert 'records' not in aggregate and aggregate['human_reviews_created'] == aggregate['model_calls'] == 0
    assert analytics.review_statistics()['reviewed_alerts'] == 0
    assert not scoped.list('feedback_events') and not scoped.list('step_runs')
    # The genuine path uses only a pending case and a new dataset namespace.
    pending_id = reserved[0]['id']
    plan = bulk_jobs.preview(scoped, [pending_id], first['baseline_id'], 'TEST_ONLY_operator')
    assert plan['eligible_cases'] == 1 and plan['dataset_id'] == first['baseline_id']
    with pytest.raises(Conflict): bulk_jobs.preview(scoped, [training[0]['id']], first['baseline_id'], 'TEST_ONLY_operator')
    with pytest.raises(Conflict): bulk_jobs.preview(scoped, [pending_id], ID, 'TEST_ONLY_operator')
    request = Start(case_ids=[pending_id], dataset_id=first['baseline_id'], selection_hash=plan['selection_hash'], idempotency_key='TEST_ONLY_baseline_row')
    batch = bulk_jobs.create(scoped, request, 'TEST_ONLY_operator')
    assert bulk_jobs.create(scoped, request, 'TEST_ONLY_operator')['id'] == batch['id']
    assert workspace.queue(scoped, status='awaiting_triage', private=True)['total'] == 1000
    queued = next(row for row in workspace.queue(scoped, identity=reserved[0]['identity_id'], private=True)['items'] if row['id'] == pending_id)
    assert queued['batch_state'] == 'QUEUED' and queued['batch_id'] == batch['id']
    public = next(row for row in workspace.queue(scoped, identity=reserved[0]['identity_id'])['items'] if row['id'] == pending_id)
    assert public['batch_state'] is None and 'batch_id' not in public
    assert 'disabled or expired' in batch['waiting_message'] and not batch['can_resume']
    assert bulk_jobs.advance(scoped, batch['id'])['state'] == 'PAUSED_CAPACITY'
    # Explicit isolated refusal exercises the real parent/child path, never a fake provider success.
    scoped.db.collection('bulk_jobs').document(batch['id']).update({'state': 'QUEUED'})
    worker, source = bulk_jobs.source(scoped, pending_id, first['baseline_id'])
    assert all(alert['dataset_id'] == first['baseline_id'] for alert in source['alerts'])
    parent_id, created = worker.enqueue_triage(batch['members'][0]['alert_ids'], 'TEST_ONLY_operator', plan['detector_policy'], plan['auto_label_policy'], bulk_member=batch['members'][0]['id'])
    assert created
    from backend.jobs import run_local
    assert run_local(worker, parent_id)
    assert worker.get('pipeline_runs', parent_id)['state'] == 'FAILED'
    assert bulk_jobs.scoped(scoped, worker.get('pipeline_runs', parent_id)).dataset_id == first['baseline_id']
    assert all(step['execution_provenance'] in {'DETERMINISTIC', 'NOT_SENT'} for step in worker.list('step_runs'))
    assert bulk_jobs.advance(scoped, batch['id'])['state'] == 'FAILED'
    assert analytics.review_statistics()['reviewed_alerts'] == 0
    with pytest.raises(Conflict): analytics.freeze_analytical_inputs('TEST_ONLY')
    with pytest.raises(Conflict): workspace.ReferenceTraining(scoped).observations('VALIDATION')
    outside = next(row['id'] for row in corpus().page(limit=100)['items'])
    with pytest.raises(LookupError): workspace.case(scoped, outside)
    # Deleting a serving chunk must fail closed rather than restore the old 40,000-case view.
    scoped.db.collection('baseline_workspace_chunks').document(active['chunks'][0]['id']).delete()
    with pytest.raises(Conflict): workspace.queue(scoped)
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
    assert "Today's AI switch is off" in job['waiting_message'] and not job['can_resume']
    with pytest.raises(Conflict): bulk_jobs.decision(repo, job['id'], job['revision'], 'resume', 'test-operator')
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
    from backend.bulk_reference import SIZE
    public_summary = client.get('/api/demo/bulk/summary').json()
    assert public_summary['reference_walkthrough_cases'] == SIZE
    assert public_summary['training_transactions'] == corpus().manifest['training_transactions']
    assert public_summary['initially_unprocessed'] == corpus().manifest['initially_unprocessed']
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
