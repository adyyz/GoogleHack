from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from backend.quick_review import inputs, reply_schema, run
from backend.repository import Conflict


def test_bulk_review_inputs_are_diverse_and_blind_to_reference_labels():
    cases = inputs()
    assert len(cases) == 5
    assert len({c['evidence']['customer']['id'] for c in cases}) == 5
    assert len({a['rule_id'] for c in cases for a in c['alerts']}) >= 5
    assert all(len(c['evidence']['history']) <= 3 and c['evidence']['omitted_history_transactions'] >= 0 for c in cases)
    assert not any(key in json.dumps(cases) for key in ['reference_verdict', 'reference_prediction', 'reference_score'])
    with pytest.raises(ValueError): inputs(6)


def test_bulk_review_rejects_missing_duplicate_and_foreign_references():
    cases = inputs()
    schema = reply_schema(cases)
    rows = [{'alert_ref': a['alert_ref'], 'verdict': 'INCONCLUSIVE', 'rationale': 'Source context is limited.',
        'evidence_ids': [c['evidence']['evidence_ids'][0]]} for c in cases for a in c['alerts']]
    assert len(schema.model_validate({'reviews': rows}).reviews) == len(rows)
    for changed in [rows[:-1], rows + [rows[0]], [dict(rows[0], evidence_ids=['invented'])] + rows[1:],
                    [dict(rows[0], alert_ref='wrong')] + rows[1:]]:
        with pytest.raises(ValueError): schema.model_validate({'reviews': changed})
    protected = next(i for i, r in enumerate(rows) if next(c for c in cases if r['alert_ref'] in {a['alert_ref'] for a in c['alerts']})['evidence']['protected_signals'])
    changed = deepcopy(rows); changed[protected]['verdict'] = 'FALSE_POSITIVE'
    assert schema.model_validate({'reviews': changed}).reviews[protected].verdict == 'FALSE_POSITIVE'


def test_bulk_review_refuses_before_access_or_writes_without_local_free_authorization():
    with pytest.raises(Conflict): run(SimpleNamespace(settings=SimpleNamespace(mode='cloud')), cases=[], baseline_id='test-only')


def test_bulk_review_refuses_reserved_cases_before_request(monkeypatch):
    from backend.bulk_dataset import SEEDED_ID
    from backend import seeded_baseline
    cases = inputs(1)
    monkeypatch.setattr(seeded_baseline, 'active', lambda _repo: {'id': 'test-baseline', 'BASELINE': [{'case_id': 'different-case'}]})
    repo = SimpleNamespace(settings=SimpleNamespace(mode='local', local_gemini_valid=lambda: True), dataset_id=SEEDED_ID)
    with pytest.raises(Conflict, match='outside the active'):
        run(repo, cases=cases, baseline_id='test-baseline')
