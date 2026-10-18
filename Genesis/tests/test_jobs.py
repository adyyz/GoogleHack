from backend.dataset import generate_dataset
from backend.engine import enrich, risk_assessment
from backend.models import Split
from backend.prompts import context_for
from backend.repository import Repository
from google.api_core.exceptions import Aborted
from types import SimpleNamespace
import pytest


def test_closed_a5_worker_seals_refusal_without_model_output():
    from backend.jobs import run_evolution
    from backend.dataset import DATASET_ID, stable_id
    rows = {("pipeline_runs", "unit-run"): {"id": "unit-run", "dataset_id": DATASET_ID,
        "config_bundle_id": "unit-bundle", "analytical_snapshot_id": "unit-snapshot", "state": "QUEUED"}}
    class Ref:
        def __init__(self, collection, ident): self.key = collection, ident
        def update(self, data): rows[self.key].update(data)
    repo = SimpleNamespace(dataset_id=DATASET_ID, settings=SimpleNamespace(active_model_id="unused", ai_authorized=lambda: False),
        claim_batch=lambda _ident, kind: kind == "EVOLUTION", get=lambda collection, ident: rows.get((collection, ident)),
        evolution_context=lambda _ident: {}, create=lambda collection, ident, data: rows.__setitem__((collection, ident), data),
        db=SimpleNamespace(collection=lambda collection: SimpleNamespace(document=lambda ident: Ref(collection, ident))))
    assert run_evolution(repo, "unit-run") is True
    step = rows[("step_runs", stable_id("unit-run", "A5", 1))]
    assert step["state"] == "FAILED" and step["error_code"] == "AI_NOT_CONNECTED"
    assert step["output"] is None and step["total_tokens"] is None
    assert step["usage_status"] == "NOT_APPLICABLE" and step["execution_provenance"] == "NOT_SENT"
    assert rows[("pipeline_runs", "unit-run")]["state"] == "FAILED"


def test_transaction_retry_requires_confirmed_abort(monkeypatch):
    repo = object.__new__(Repository)
    repo.db = SimpleNamespace(transaction=object)
    monkeypatch.setattr("backend.repository.sleep", lambda _seconds: None)
    seen = []

    def aborted_once(tx):
        seen.append(tx)
        if len(seen) == 1:
            try: raise Aborted("lock timeout")
            except Aborted as exc: raise ValueError("SDK retry exhaustion") from exc
        return True

    assert repo._contended_transaction(aborted_once) is True
    assert len(seen) == 2 and seen[0] is not seen[1]
    def unknown(_tx): raise ValueError("unknown commit outcome")
    with pytest.raises(ValueError, match="unknown commit"):
        repo._contended_transaction(unknown)


def test_context_preserves_facts_and_protected_sequence_without_labels():
    data = generate_dataset()
    case = next(case for case in data.cases.values() if case.split == Split.DEMO and case.scenario_family == "structuring")
    evidence = enrich(data, case)
    context = context_for("A2", evidence, risk_assessment(evidence), {})
    assert context["facts"] == evidence["facts"]
    assert context["protected_signals"] == evidence["protected_signals"]
    assert set(context["evidence_ids"]) <= set(evidence["evidence_ids"])
    assert all(transaction["id"] in context["evidence_ids"] for transaction in context["chronology"])
    assert len([transaction for transaction in [context["trigger"], *context["chronology"]] if transaction["type"] == "CASH"]) >= 3
    assert "reference_labels" not in context and "reference_reasons" not in context
    # Classification consumes code-owned risk/facts, not a duplicated narrative history.
    classification = context_for("A3", evidence, risk_assessment(evidence), {"A2": {"limitations": ["test-only"]}})
    assert classification["previous_outputs"]["A2_advisory"]["status"] == "NOT_RECORDED" and "chronology" not in classification
    assert classification["risk"] == risk_assessment(evidence)
    assert set(classification["evidence_ids"]) == {evidence[key]["id"] for key in ("customer", "account", "trigger")}
    assert len(classification["evidence_ids"]) < len(evidence["evidence_ids"])
    assert evidence["evidence_ids"] == enrich(data, case)["evidence_ids"]  # Never mutate frozen evidence.


def test_long_history_is_bounded_without_losing_protected_deposits_or_source_facts():
    from copy import deepcopy
    from datetime import datetime, timedelta
    data = generate_dataset()
    case = next(case for case in data.cases.values() if case.split == Split.DEMO and case.scenario_family == 'structuring')
    evidence = enrich(data, case)
    at = datetime.fromisoformat(evidence['trigger']['occurred_at'])
    template = evidence['trigger']
    deposits = [{**template, 'id': f'deposit-{n}', 'occurred_at': (at - timedelta(hours=48-n)).isoformat(),
        'type': 'CASH', 'direction': 'CREDIT', 'amount_aud_minor': 900_000} for n in range(3)]
    later = [{**template, 'id': f'later-{n}', 'occurred_at': (at - timedelta(hours=24-n)).isoformat(), 'type': 'WIRE'} for n in range(20)]
    evidence['history'] = deposits + later
    evidence['evidence_ids'] = [evidence[key]['id'] for key in ('customer', 'account', 'trigger')] + [row['id'] for row in evidence['history']]
    before = deepcopy(evidence)
    for leg in ('A2', 'A4'):
        selected = context_for(leg, evidence, risk_assessment(evidence), {})
        ids = {row['id'] for row in selected['chronology']}
        assert len(ids) == 8 and {row['id'] for row in deposits} <= ids
        assert later[-1]['id'] in ids
        assert selected['chronology_selection']['omitted'] == 15
        assert selected['facts'] == evidence['facts'] and selected['protected_signals'] == evidence['protected_signals']
        assert ids <= set(selected['evidence_ids']) <= set(evidence['evidence_ids'])
    assert evidence == before


def test_context_refusal_preserves_precount_without_provider_usage():
    from backend.jobs import _model_attempt
    from backend.gateway import GatewayResult
    from backend.models import StepRun
    from backend.repository import now
    rows = {}
    repo = SimpleNamespace(get=lambda collection, ident: rows.get(ident),
        create=lambda collection, ident, body: rows.__setitem__(ident, body))
    step = StepRun(id='count-refused', dataset_id='test', run_id='test-run', leg_id='A2', config_bundle_id='test-bundle',
        state='STARTED', started_at=now(), input_hash='test-input')
    row = _model_attempt(repo, step, lambda _: GatewayResult(error_code='CONTEXT_LIMIT', context_precount_tokens=4097))
    assert row['state'] == 'FAILED' and row['execution_provenance'] == 'NOT_SENT'
    assert row['context_precount_tokens'] == 4097
    assert row['usage_status'] == row['cost_status'] == 'NOT_APPLICABLE'
    assert row['total_tokens'] is None and row['output'] is None


def test_model_step_uses_one_linked_retry_and_never_repeats_sealed_attempts(monkeypatch):
    from backend.dataset import DATASET_ID, stable_id
    from backend.gateway import GatewayResult
    from backend.jobs import _model_step
    from backend.models import StepRun
    from backend.repository import now
    rows, calls, waits = {}, [], []
    step = StepRun(id=stable_id("unit-run", "A3", 1), dataset_id=DATASET_ID, run_id="unit-run", leg_id="A3",
        config_bundle_id="unit-bundle", state="STARTED", started_at=now(), input_hash="unit-input",
        usage_status="UNKNOWN", cost_status="UNKNOWN", execution_provenance="UNKNOWN")
    bundle = {"body": {"attempts_per_leg": 2}}
    repo = SimpleNamespace(get=lambda collection, ident: bundle if collection == "config_versions" else rows.get(ident))
    monkeypatch.setattr("backend.jobs.sleep", waits.append)
    def reject(attempt):
        calls.append(attempt)
        rows[attempt.id] = {**attempt.model_dump(), "state": "FAILED", "finished_at": now(), "output": None,
            "execution_provenance": "REAL_PROVIDER", "error_code": "PROVIDER_HTTP_429", "retry_delay_seconds": 1}
        return GatewayResult(outcome="FAILED", error_code="PROVIDER_HTTP_429", step_id=attempt.id)
    result, error = _model_step(repo, step, reject, {})
    assert error == "PROVIDER_HTTP_429" and result["attempt_number"] == 2
    assert len(calls) == 2 and waits == [1] and calls[1].retry_of_step_id == step.id
    assert _model_step(repo, step, reject, {}) == (result, error)
    assert len(calls) == 2 and waits == [1]
    bundle["body"]["attempts_per_leg"] = 1
    assert _model_step(repo, step, reject, {})[0]["attempt_number"] == 1
    assert len(calls) == 2  # Old frozen policies never gain a retry silently.
    for state, code, provenance in [("UNKNOWN_OUTCOME", "PROVIDER_OUTCOME_UNKNOWN", "UNKNOWN"),
        ("FAILED", "CAP_REACHED", "NOT_SENT"), ("FAILED", "CREDIT_VERIFICATION_EXPIRED", "NOT_SENT"),
        ("FAILED", "PROVIDER_HTTP_403", "REAL_PROVIDER")]:
        rows[step.id].update(state=state, error_code=code, execution_provenance=provenance)
        assert _model_step(repo, step, reject, {})[1] == code
        assert len(calls) == 2
