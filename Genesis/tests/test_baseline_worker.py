"""Scheduling-only fixture: no provider output, feedback or Firestore writes."""
from types import SimpleNamespace
from backend import jobs, baseline_workspace, bulk_jobs


def test_worker_ticks_only_the_active_baseline_and_advances_after_sealing(monkeypatch):
    scope = 'a' * 64
    reads, events = [], []
    def page(collection, limit, *, filters):
        reads.append(filters)
        if collection == 'bulk_jobs': return {'items': [{'id': 'job'}]}
        return {'items': [{'id': 'triage' if ('kind', 'TRIAGE_BATCH') in filters else 'evolution'}]}
    repo = SimpleNamespace(settings=SimpleNamespace(mode='local', local_gemini_enabled=True), page=page)
    monkeypatch.setattr(baseline_workspace, 'selected_id', lambda _: scope)
    monkeypatch.setattr(bulk_jobs, 'advance', lambda _repo, ident: events.append(('advance', ident)))
    monkeypatch.setattr(bulk_jobs, 'scoped', lambda _repo, row: repo)
    monkeypatch.setattr(jobs, 'run_local', lambda _repo, ident: events.append(('triage', ident)) or True)
    monkeypatch.setattr(jobs, 'run_evolution', lambda _repo, ident: events.append(('evolution', ident)) or True)
    assert jobs.worker_once(repo) == 2
    assert all(('dataset_id', scope) in filters for filters in reads)
    assert events == [('advance', 'job'), ('triage', 'triage'), ('advance', 'job'), ('evolution', 'evolution')]
