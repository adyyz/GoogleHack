from copy import deepcopy
from types import SimpleNamespace

import pytest

from backend.dataset import generate_dataset
from backend.engine import auto_label, enrich, retains_high_value, candidate_options
from backend.evolution import analytical_inputs
from backend.models import FeedbackRequest
from backend.repository import Conflict, Repository


def test_evolution_projection_preserves_counts_counter_evidence_and_omission_counts():
    from backend.prompts import evolution_prompt_context
    counts = {key: 1 for key in ('reviewed_alerts', 'true_positive', 'false_positive', 'inconclusive', 'compared', 'agreed', 'suggestion_unavailable', 'machine_uncertain')}
    row = {"name": "HIGH_VALUE", **counts}
    finding = {"text": "Original fixture finding", "evidence_ids": ["source"]}
    context = {"analytical_inputs": {"computed_statistics": {"groups": {"rule": [row]}}},
        "human_feedback": [{"id": "f", "rule_id": "HIGH_VALUE", "triage_run_id": "run", "verdict": "FALSE_POSITIVE"}],
        "recorded_python_evidence": [{"run_id": "run", "signals": ["HIGH_VALUE"]}, {"run_id": "outside", "signals": []}],
        "sealed_model_suggestions": [{"run_id": "run", "leg_id": "A2", "output": {
            "findings": [finding, finding], "counter_evidence": [finding, finding], "limitations": ["Fixture only"]}}]}
    original = deepcopy(context); projected = evolution_prompt_context(context)
    group = projected['analytical_inputs']['computed_statistics']['groups']['rule']
    assert dict(zip(group['columns'], group['rows'][0])) == row and context == original
    assert projected['sealed_model_suggestions'][0]['output']['counter_evidence'] == [finding]
    assert projected['selection']['narrative_omitted'][0]['omitted_items'] == {'findings': 1, 'counter_evidence': 1, 'limitations': 1}
    assert len(projected['recorded_python_evidence']) == 1 and len(projected['rule_catalog']) == 9
from backend.review_metrics import review_summary


def test_evolution_prompt_preserves_analytical_evidence_without_ledger_hashes():
    from backend.prompts import evolution_prompt_context
    context = {"analytical_inputs": {"succeeded_steps": [{"id": "step", "hash": "opaque"}],
        "usage_steps": [{"id": "attempt"}], "detector_gate": {"conclusive_reviews": 2},
        "usage": {"total_tokens": 9000}}, "human_feedback": [{"id": "f", "rule_id": "HIGH_VALUE", "triage_run_id": "r", "verdict": "TRUE_POSITIVE"}],
        "sealed_model_suggestions": [{"run_id": "r", "leg_id": "A3", "output": {"primary_typology": "OTHER", "suggested_action": "REVIEW", "uncertainty": "LOW"}}]}
    original = deepcopy(context)
    projected = evolution_prompt_context(context)
    assert context == original
    assert "succeeded_steps" not in projected["analytical_inputs"]
    assert "usage_steps" not in projected["analytical_inputs"]
    assert projected["analytical_inputs"]["detector_gate"] == {"conclusive_reviews": 2}
    assert projected["analytical_inputs"]["usage"] == {"total_tokens": 9000}
    assert projected["human_feedback"] == context["human_feedback"]
    assert projected["sealed_model_suggestions"] == context["sealed_model_suggestions"]


def test_auto_label_is_separate_from_verdict_and_forces_guarded_review():
    evidence = {"missing_context": [], "protected_signals": []}
    classification = {"primary_typology": "LOW_RISK", "suggested_action": "CLOSE", "uncertainty": "LOW"}
    result = auto_label(evidence, classification)
    assert result["predicted_verdict"] == "AUTO_FP" and result["heuristic_score"] == .8
    assert result["score_is_probability"] is False
    assert "verdict" not in result and "priority" not in result
    assert auto_label(evidence, {**classification, "suggested_action": "REVIEW"})["predicted_verdict"] == "AUTO_UNCERTAIN"
    assert auto_label(evidence, {**classification, "primary_typology": "OTHER", "suggested_action": "REVIEW"})["predicted_verdict"] == "AUTO_TP"
    for guarded in ({**evidence, "missing_context": ["history"]}, {**evidence, "protected_signals": ["STRUCTURING"]}):
        assert auto_label(guarded, classification)["predicted_verdict"] == "AUTO_UNCERTAIN"


def test_brief_context_bounds_prior_narratives_without_rewriting_evidence():
    from backend.prompts import context_for
    from backend.engine import risk_assessment
    data = generate_dataset()
    evidence = enrich(data, next(iter(data.cases.values())))
    finding = {"text": "Short cited source finding", "evidence_ids": [evidence["trigger"]["id"]]}
    previous = {"A2": {"findings": [{**finding, "text": "x" * 601}, finding, finding], "counter_evidence": [finding], "limitations": ["Known limit"]},
        "A3": {"primary_typology": "OTHER", "suggested_action": "REVIEW", "uncertainty": "HIGH", "rationale": {**finding, "evidence_ids": ["x"] * 4}}}
    before = deepcopy(previous)
    selected = context_for("A4", evidence, risk_assessment(evidence), previous)
    assert selected["facts"] == evidence["facts"] and selected["protected_signals"] == evidence["protected_signals"]
    assert selected["previous_outputs"]["A2"]["findings"] == [finding]
    assert selected["prior_narrative_selection"]["A2_omitted"]["findings"] == 2
    assert selected["prior_narrative_selection"]["A3_rationale_omitted"]
    assert previous == before and evidence == enrich(data, next(iter(data.cases.values())))


def test_review_counts_use_machine_labels_on_the_reviewed_run_and_unknown_denominators():
    cases = [{"id": "case", "customer_id": "person", "split": "DEMO"}]
    customers = [{"id": "person", "customer_type": "INDIVIDUAL"}]
    alerts = [{"id": str(index), "case_id": "case", "rule_id": "HIGH_VALUE"} for index in range(3)]
    feedback = [{"id": str(index), "alert_id": str(index), "case_id": "case", "triage_run_id": str(index),
        "revision": 1, "verdict": verdict, "provenance": "HUMAN_OPERATOR"}
        for index, verdict in enumerate(["TRUE_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE"])]
    steps = [{"run_id": "0", "leg_id": "A0", "state": "SUCCEEDED", "execution_provenance": "DETERMINISTIC",
        "validation": {"schema_pass": True, "evidence_pass": True}, "output": {"predicted_verdict": "AUTO_TP"}},
        {"run_id": "different-run", "leg_id": "A0", "state": "SUCCEEDED", "execution_provenance": "DETERMINISTIC",
        "validation": {"schema_pass": True, "evidence_pass": True}, "output": {"predicted_verdict": "AUTO_FP"}}]
    result = review_summary(cases, customers, alerts, feedback, steps)
    assert result["reviewed_cases"] == 1 and result["reviewed_alerts"] == 3
    assert result["compared"] == result["agreed"] == 1 and result["suggestion_unavailable"] == 2
    assert result["true_positive"] == result["false_positive"] == result["inconclusive"] == 1
    assert result["population_accuracy"] is None and result["population_fpr"] is None
    assert result["groups"]["identity_type"][0]["name"] == "INDIVIDUAL"
    assert review_summary(cases, customers, alerts, [], [])['agreement_rate'] is None


def test_pattern_inputs_deduplicate_reviews_and_keep_policy_versions_separate():
    alerts = [{"id": str(i), "rule_id": "HIGH_VALUE"} for i in range(3)]
    feedback = [{"id": f"{i}-1", "alert_id": str(i), "triage_run_id": str(i), "revision": 1,
        "verdict": "FALSE_POSITIVE", "detector_policy_id": "detector-v1" if i < 2 else "different-policy"} for i in range(3)]
    steps = [{"id": str(i), "run_id": str(i), "leg_id": "A3", "state": "SUCCEEDED", "config_bundle_id": "test-only",
        "output": {"primary_typology": "LOW_RISK"}} for i in range(3)]
    first = analytical_inputs("test-source", feedback, steps, alerts)
    assert first == analytical_inputs("test-source", feedback, steps, alerts)
    assert sorted(len(row["support_feedback_ids"]) for row in first["pattern_memory"]) == [1, 2]
    revised = [*feedback, {**feedback[0], "id": "0-2", "revision": 2, "verdict": "TRUE_POSITIVE"}]
    assert sum(len(row["support_feedback_ids"]) for row in analytical_inputs("test-source", revised, steps, alerts)["pattern_memory"]) == 2


def test_policy_filter_is_the_same_as_frozen_detector_replay():
    from backend.engine import detect
    data = generate_dataset()
    for case in data.cases.values():
        evidence = enrich(data, case)
        for candidate in candidate_options():
            baseline = {row['rule_id'] for row in detect(data, case)}
            filtered = {row['rule_id'] for row in detect(data, case, candidate)}
            assert ('HIGH_VALUE' in filtered) == ('HIGH_VALUE' in baseline and retains_high_value(evidence, candidate))
            assert baseline - filtered <= {'HIGH_VALUE'}


def test_history_joins_all_accounts_of_one_identity_without_changing_sources():
    from datetime import timedelta
    data = generate_dataset()
    case = next(iter(data.cases.values()))
    trigger = data.transactions[case.trigger_transaction_id]
    original = data.model_dump()
    other_account = data.accounts[trigger.account_id].model_copy(update={"id": "unit-other-account"})
    transaction = trigger.model_copy(update={"id": "unit-cross-account", "account_id": other_account.id,
        "occurred_at": trigger.occurred_at - timedelta(days=2)})
    expanded = data.model_copy(update={"accounts": {**data.accounts, other_account.id: other_account},
        "transactions": {**data.transactions, transaction.id: transaction}})
    evidence = enrich(expanded, case)
    assert evidence["customer"]["id"] == other_account.customer_id
    assert any(row["id"] == transaction.id and row["account_id"] == other_account.id for row in evidence["history"])
    assert data.model_dump() == original


def test_frozen_review_refuses_before_any_new_feedback_or_lineage_read(monkeypatch):
    repo = object.__new__(Repository)
    snapshot = SimpleNamespace(exists=True, to_dict=lambda: {"dataset_id": "synthetic-v1-20261015", "feedback_revision": 1})
    ref = SimpleNamespace(get=lambda **_kwargs: snapshot)
    repo.db = SimpleNamespace(collection=lambda _name: SimpleNamespace(document=lambda _id: ref), transaction=lambda: object())
    monkeypatch.setattr("backend.repository.firestore.transactional", lambda operation: operation)
    with pytest.raises(Conflict, match="frozen"):
        repo.save_feedback("test-only", FeedbackRequest(verdict="FALSE_POSITIVE", notes="Pure unit fixture", expected_revision=1), "test-only")


def test_application_evidence_refuses_insufficiency_tampering_and_no_benefit():
    """Pure memory fixtures; never stored as genuine AI/evaluation evidence."""
    from datetime import datetime, timedelta, timezone
    from backend.dataset import DATASET_ID, content_hash, stable_id
    from backend.evolution import candidate_identity
    instant = datetime.now(timezone.utc)
    candidate = candidate_options()[0]
    body = {"dataset_hash": "unit-source", "detector_gate": {"conclusive_reviews": 30, "target_rule_reviews": 15}}
    snapshot_id = content_hash(body)
    run = {"id": "unit-a5", "kind": "EVOLUTION", "state": "COMPLETE", "dataset_id": DATASET_ID,
        "analytical_snapshot_id": snapshot_id, "config_bundle_id": "unit-config"}
    frozen_body = {"evolution_run_id": run["id"], "support_status": "FEEDBACK_SUPPORTED",
        "candidate_hash": candidate_identity("unit-source", candidate)}
    frozen = {**frozen_body, "id": stable_id(DATASET_ID, "heldout"), "content_hash": content_hash(frozen_body), "frozen_at": instant}
    simulation = {"state": "COMPLETE", "candidate_hash": frozen["candidate_hash"], "freeze_hash": frozen["content_hash"],
        "started_at": instant + timedelta(seconds=1), "metrics": {"provenance": "DETERMINISTIC_SYNTHETIC_REFERENCE_REPLAY",
        "dataset_hash": "unit-source", "candidate": candidate, "case_ids": ["unit-case"], "benign_alerts_removed": 2, "additional_missed_case_ids": []}}
    store = {("recommendations", run["id"]): {"dataset_id": DATASET_ID, "candidate": candidate},
        ("pipeline_runs", run["id"]): run, ("analytical_snapshots", snapshot_id): {"body": body},
        ("candidate_freezes", frozen["id"]): frozen, ("simulations", frozen["id"]): simulation}
    step = {"state": "SUCCEEDED", "execution_provenance": "REAL_PROVIDER", "config_bundle_id": "unit-config",
        "dataset_id": DATASET_ID, "validation": {"schema_pass": True, "evidence_pass": True},
        "output": {"status": "SUPPORTED_PROPOSAL", "candidate_id": candidate["id"]}}
    repo = object.__new__(Repository)
    def document(collection, ident):
        value = store.get((collection, ident))
        return SimpleNamespace(get=lambda **_kwargs: SimpleNamespace(id=ident, exists=value is not None, to_dict=lambda: deepcopy(value)))
    repo.db = SimpleNamespace(collection=lambda name: SimpleNamespace(document=lambda ident: document(name, ident)))
    repo._leg_step = lambda *_args: deepcopy(step)
    assert repo.application_evidence(run["id"])["candidate"] == candidate
    simulation["metrics"]["benign_alerts_removed"] = 0
    with pytest.raises(Conflict, match="No measured safe benefit"): repo.application_evidence(run["id"])
    simulation["metrics"]["benign_alerts_removed"] = 2
    simulation["metrics"]["additional_missed_case_ids"] = ["unit-case"]
    with pytest.raises(Conflict, match="No measured safe benefit"): repo.application_evidence(run["id"])
    simulation["metrics"]["additional_missed_case_ids"] = []
    frozen["support_status"] = "OPERATOR_SELECTED_NOT_FEEDBACK_SUPPORTED"
    with pytest.raises(Conflict, match="supported frozen"): repo.application_evidence(run["id"])
    frozen["support_status"] = "FEEDBACK_SUPPORTED"
    frozen["unexpected"] = "tampered"
    with pytest.raises(Conflict, match="integrity"): repo.application_evidence(run["id"])
