"""Isolated simulated fixtures only; no provider output or human verdict is written."""
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace

import pytest

from backend import projected_reviews as projection
from backend.bulk_dataset import SEEDED_ID
from backend.dataset import content_hash
from backend.engine import RULES


@pytest.fixture
def sample(monkeypatch):
    rows, advisories, sources = [], [], {}
    for index in range(2000):
        case_id = f'TEST_ONLY_case_{index}'
        rule = list(RULES)[index % 9]
        manual = rule in {'POST_DEATH', 'STRUCTURING'}
        row = {'id': case_id, 'identity_id': f'TEST_ONLY_identity_{index % 80}', 'balance_rule': rule,
            'heuristic_score': [.1, .5, .8][index % 3], 'reference': True}
        rows.append(row)
        alert = {'alert_id': f'TEST_ONLY_alert_{index}', 'rule_id': rule, 'alert_ref': 'C1A1'}
        sources[case_id] = {'alerts': [{'id': alert['alert_id'], 'rule_id': rule}],
            'evidence': {'protected_signals': ['TEST_ONLY'] if manual else [], 'missing_context': [], 'evidence_ids': [case_id]}}
        advisories.append({'id': f'TEST_ONLY_advisory_{index}', 'case_id': case_id, 'baseline_id': 'TEST_ONLY_BASELINE',
            'dataset_id': SEEDED_ID, 'provenance': 'LOCAL_AGENT_DRAFT_ADVISORY_NOT_HUMAN', 'human_review': False,
            'requires_manual_review': manual, 'alert_mapping': [alert],
            'reviews': [{'alert_ref': 'C1A1', 'verdict': ['TRUE_POSITIVE', 'FALSE_POSITIVE', 'INCONCLUSIVE'][index % 3], 'evidence_ids': [case_id]}]})
    monkeypatch.setattr(projection, 'corpus', lambda: SimpleNamespace(case=lambda ident: deepcopy(sources[ident])))
    return rows, advisories


def test_exact_stratified_case_allocation_is_reproducible_and_preserves_unknowns(sample):
    rows, advisories = sample
    original = content_hash(advisories)
    records = projection.build(rows, advisories, 'TEST_ONLY_BASELINE')
    assert Counter(row['body']['assignment'] for row in records) == {'AGREE': 1500, 'DISAGREE': 400, 'UNCERTAIN': 100}
    assert projection.assignments(rows, 'TEST_ONLY_BASELINE') == projection.assignments(list(reversed(rows)), 'TEST_ONLY_BASELINE')
    result = projection.aggregate(records, 'TEST_ONLY_BASELINE')
    assert len(result['rules']) == 9 and all(row['balancing_assignment_counts'].get('DISAGREE', 0) > 0 for row in result['rules'])
    assert all(row['balancing_assignment_counts'].get('UNCERTAIN', 0) > 0 for row in result['rules'])
    assert sum(row['inconclusive'] for row in result['rules']) > 100
    assert projection.project('INCONCLUSIVE', 'DISAGREE') == 'INCONCLUSIVE'
    assert projection.project('TRUE_POSITIVE', 'DISAGREE') == 'FALSE_POSITIVE'
    assert projection.project('FALSE_POSITIVE', 'DISAGREE') == 'TRUE_POSITIVE'
    assert all(not row['body']['human_review'] and not row['body']['human_verified'] for row in records)
    assert all(not row['operationally_applicable'] and row['validation'] == 'NOT_PERFORMED' for row in result['fitting_results'])
    assert all(row['eligible_observations'] == 0 for row in result['fitting_results'] if row['rule_id'] in {'POST_DEATH', 'STRUCTURING'})
    assert content_hash(advisories) == original


def test_validation_precedes_all_writes_and_repeated_import_creates_nothing(sample, monkeypatch):
    rows, advisories = sample
    store, writes = {}, []
    def create(collection, ident, body):
        writes.append(collection); store[(collection, ident)] = deepcopy(body)
    class Batch:
        def __init__(self): self.records = []
        def create(self, ref, body): self.records.append((*ref, body))
        def commit(self, **_kwargs):
            for collection, ident, body in self.records: create(collection, ident, body)
    class Document:
        def __init__(self, collection, ident): self.collection, self.ident = collection, ident
        def set(self, body): create(self.collection, self.ident, body)
        def __iter__(self): return iter((self.collection, self.ident))
    db = SimpleNamespace(batch=Batch, collection=lambda name: SimpleNamespace(document=lambda ident: Document(name, ident)))
    repo = SimpleNamespace(settings=SimpleNamespace(mode='local', project_id='demo-aml-insight'), db=db,
        list=lambda collection, dataset: advisories if collection == 'seeded_advisory_reviews' else [{'id': ident, **body} for (name, ident), body in store.items() if name == collection],
        get=lambda collection, ident: store.get((collection, ident)), create=create)
    monkeypatch.setattr(projection.workspace, 'view', lambda _: {'baseline_id': 'TEST_ONLY_BASELINE'})
    monkeypatch.setattr(projection.workspace, 'selected_id', lambda _: 'TEST_ONLY_BASELINE')
    monkeypatch.setattr(projection.workspace, 'rows', lambda *_: rows)
    assert projection.prepare(repo)['would_create'] == 2000 and not writes
    original = advisories[-1]['reviews'][0]['verdict']
    advisories[-1]['reviews'][0]['verdict'] = 'MALFORMED_FINAL_RECORD'
    with pytest.raises(ValueError): projection.prepare(repo, apply=True)
    assert not writes
    advisories[-1]['reviews'][0]['verdict'] = original
    assert projection.prepare(repo, apply=True)['created'] == 2000
    assert projection.prepare(repo, apply=True)['created'] == 0
    assert set(writes) == {'projected_analyst_reviews', 'projected_review_runs', 'projected_review_controls'}
    result = projection.summary(repo)
    assert result['prepared'] and result['cases'] == 2000 and result['human_reviews_created'] == result['model_calls'] == 0
    assert 'records' not in result


@pytest.mark.parametrize('fault', ['duplicate', 'reserved', 'foreign_citation', 'wrong_rule'])
def test_projection_rejects_foreign_or_mismatched_advisories(sample, fault):
    rows, advisories = sample
    if fault == 'duplicate': advisories[-1] = deepcopy(advisories[0])
    if fault == 'reserved': advisories[-1]['case_id'] = 'TEST_ONLY_RESERVED'
    if fault == 'foreign_citation': advisories[-1]['reviews'][0]['evidence_ids'] = ['ANOTHER_CASE']
    if fault == 'wrong_rule': advisories[-1]['alert_mapping'][0]['rule_id'] = 'ANOTHER_RULE'
    with pytest.raises(ValueError): projection.build(rows, advisories, 'TEST_ONLY_BASELINE')
