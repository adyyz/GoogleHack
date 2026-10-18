from collections import Counter
from backend.seeded_baseline import selection, describe


def test_progress_separates_gemini_and_agent_drafts(monkeypatch):
    from types import SimpleNamespace
    from backend import seeded_baseline
    monkeypatch.setattr(seeded_baseline, 'active', lambda _repo: {'id': 'test-only', 'body': {'training': {}, 'reserved': {}}})
    class Query:
        def __init__(self, drafted=False): self.drafted = drafted
        def where(self, *, filter): return Query(filter.field_path == 'provenance')
        def count(self): return self
        def get(self, **_kwargs): return [[SimpleNamespace(value=3 if self.drafted else 5)]]
    repo = SimpleNamespace(db=SimpleNamespace(collection=lambda _name: Query()))
    result = seeded_baseline.progress(repo)
    assert result['ai_reviewed_cases'] == 2 and result['agent_draft_reviewed_cases'] == 3
    assert result['pending_ai_reviews'] == 1995 and result['human_reviews'] == 0


def test_three_thousand_baseline_is_balanced_disjoint_and_reference_only():
    training, reserved = selection()
    assert len(training) == 2000 and len(reserved) == 1000
    assert len({r['id'] for r in training + reserved}) == 3000
    assert not {r['identity_id'] for r in training} & {r['identity_id'] for r in reserved}
    for rows in [training, reserved]:
        assert all(r['partition'] == 'TRAIN' for r in rows)
        summary = describe(rows)
        assert all(r['alerts'] > 0 and r['balancing_cases'] > 0 for r in summary['rules'])
        assert set(summary['identity_types']) == {'INDIVIDUAL', 'ORGANIZATION'}
        assert sum(summary['reference_verdicts'].values()) == len(rows)
        assert len({r['identity_id'] for r in rows}) > 30
    again = selection()
    assert [[r['id'] for r in rows] for rows in again] == [[r['id'] for r in rows] for rows in [training, reserved]]
