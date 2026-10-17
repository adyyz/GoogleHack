"""Pure aggregation fixtures never enter the application ledger."""
from backend.dataset import content_hash
from backend.evolution import analytical_inputs, sufficiency
from backend.evolution import candidate_identity
from backend.engine import candidate_options
from backend.models import EvolutionAssessment
from backend.validation import validate_model_output
import pytest


def test_sufficiency_requires_both_actual_denominators():
    for overall, target in [(0, 0), (29, 15), (30, 14)]:
        assert sufficiency(overall, target)["status"] == "INSUFFICIENT_EVIDENCE"
    assert sufficiency(30, 15)["status"] == "SUFFICIENT_EVIDENCE"


def test_snapshot_counts_latest_alert_reviews_and_deduplicates_inputs():
    alerts = [{"id": "a", "rule_id": "HIGH_VALUE"}, {"id": "b", "rule_id": "STRUCTURING"}]
    events = [{"id": "a-1", "alert_id": "a", "revision": 1, "verdict": "FALSE_POSITIVE"},
        {"id": "a-2", "alert_id": "a", "revision": 2, "verdict": "INCONCLUSIVE"},
        {"id": "b-1", "alert_id": "b", "revision": 1, "verdict": "TRUE_POSITIVE"}]
    body = analytical_inputs("frozen-source", events, [], alerts)
    assert body["sample_sizes"] == {"feedback_events": 3, "reviewed_alerts": 2, "conclusive_reviews": 1,
        "inconclusive_reviews": 1, "succeeded_steps": 0, "usage_steps": 0}
    assert body["rules"]["HIGH_VALUE"]["target_rule_reviews"] == 0
    assert body["rules"]["HIGH_VALUE"]["reviewed_alert_noise_proportion"] is None
    assert body["rules"]["STRUCTURING"]["true_positive_reviews"] == 1
    assert body["population_recall"] is None and body["population_fpr"] is None
    assert content_hash(body) == content_hash(analytical_inputs("frozen-source", list(reversed(events)), [], list(reversed(alerts))))
    projections = [{**alert, "status": "RUNNING", "feedback_revision": 99} for alert in alerts]
    assert content_hash(body) == content_hash(analytical_inputs("frozen-source", events, [], projections))
    assert body["usage"]["total_tokens"] is None and body["activation_allowed"] is False


def test_snapshot_usage_includes_failures_without_inventing_success_or_cost():
    steps = [{"id": "failed-attempt", "config_bundle_id": "frozen-bundle", "state": "UNKNOWN_OUTCOME",
        "usage_status": "UNKNOWN", "cost_status": "UNKNOWN", "output": None}]
    body = analytical_inputs("frozen-source", [], steps, [])
    assert body["succeeded_steps"] == [] and len(body["usage_steps"]) == 1
    assert body["usage"]["unknown_attempts"] == 1 and body["usage"]["total_tokens"] is None
    assert body["config_bundle_ids"] == ["frozen-bundle"]
    assert body["label_provenance"] == "HUMAN_OPERATOR_ONLY"


def test_a5_cannot_invent_counts_support_or_candidate():
    evidence = {"evidence_ids": ["review-1"], "analytical_inputs": {"detector_gate": sufficiency(1, 1)},
        "human_feedback": [{"id": "review-1", "rule_id": "HIGH_VALUE", "verdict": "FALSE_POSITIVE"}]}
    result = EvolutionAssessment(status="INSUFFICIENT_EVIDENCE", conclusive_reviews=1, target_rule_reviews=1,
        target_rule="HIGH_VALUE", summary="Unit fixture, not a provider result", limitations=["Small sample"])
    assert validate_model_output(result, evidence)["semantic_support"] == "REQUIRES_MANUAL_REVIEW"
    with pytest.raises(ValueError, match="sample sizes"):
        validate_model_output(result.model_copy(update={"conclusive_reviews": 30}), evidence)
    with pytest.raises(ValueError, match="Insufficient"):
        validate_model_output(result.model_copy(update={"status": "SUPPORTED_PROPOSAL", "candidate_id": "hv-15000",
            "hypothesis": "Fixture", "support_feedback_ids": ["review-1"]}), evidence)
    with pytest.raises(ValueError, match="without a proposal"):
        validate_model_output(result.model_copy(update={"candidate_id": "hv-15000"}), evidence)
    evidence["analytical_inputs"]["detector_gate"] = sufficiency(30, 15)
    result = result.model_copy(update={"status": "SUPPORTED_PROPOSAL", "conclusive_reviews": 30,
        "target_rule_reviews": 15, "candidate_id": "hv-15000", "hypothesis": "Fixture", "support_feedback_ids": ["review-1"]})
    assert validate_model_output(result, evidence)["citation_id_validity"]
    for invalid in [["unknown-review"], ["review-1", "review-1"], []]:
        with pytest.raises(ValueError, match="target-rule support"):
            validate_model_output(result.model_copy(update={"support_feedback_ids": invalid}), evidence)


def test_candidate_identity_pins_source_and_allowlisted_spec():
    candidate = candidate_options()[0]
    identity = candidate_identity("source-1", candidate)
    assert identity == candidate_identity("source-1", dict(candidate))
    assert identity != candidate_identity("source-2", candidate)
    assert identity != candidate_identity("source-1", candidate_options()[1])
    with pytest.raises(ValueError, match="allowlisted"):
        candidate_identity("source-1", {**candidate, "threshold_aud_minor": 1})


def test_simulation_requires_durable_freeze_and_returns_existing_result(monkeypatch):
    """An in-memory control-flow fixture; no application records or held-out labels."""
    from types import SimpleNamespace
    from backend.dataset import DATASET_ID
    from backend.repository import Conflict, Repository
    rows, calls = {}, []
    candidate = candidate_options()[0]
    body = {"dataset_hash": "fixture-source", "candidate": candidate,
        "candidate_hash": candidate_identity("fixture-source", candidate), "activation_allowed": False}
    rows[("candidate_freezes", "fixture")] = {"id": "fixture", "dataset_id": DATASET_ID,
        **body, "content_hash": content_hash(body)}
    repo = object.__new__(Repository)
    repo.get = lambda collection, ident: rows.get((collection, ident))

    class Ref:
        def __init__(self, collection, ident): self.key, self.id = (collection, ident), ident
        def get(self, **_kwargs):
            return SimpleNamespace(exists=self.key in rows, id=self.id, to_dict=lambda: rows.get(self.key))
        def update(self, data): rows[self.key].update(data)
    class Writes:
        def create(self, ref, data):
            assert ref.key not in rows
            rows[ref.key] = data
        def update(self, ref, data): ref.update(data)
        def commit(self, **_kwargs): pass
    repo.db = SimpleNamespace(collection=lambda name: SimpleNamespace(document=lambda ident: Ref(name, ident)), batch=Writes)
    repo._contended_transaction = lambda operation: operation(Writes())
    monkeypatch.setattr("backend.repository.firestore.transactional", lambda operation: operation)
    def load():
        assert rows[("simulations", "fixture")]["state"] == "RUNNING"
        calls.append("opened")
        return SimpleNamespace(manifest_hash="fixture-source")
    repo.load_dataset = load
    monkeypatch.setattr("backend.engine.simulate", lambda _data, _candidate, split: {"unit_fixture_only": True, "split": split})
    with pytest.raises(LookupError): repo.simulate_frozen("missing", "unit-operator")
    assert calls == []
    result = repo.simulate_frozen("fixture", "unit-operator")
    assert result["state"] == "COMPLETE" and calls == ["opened"]
    assert repo.simulate_frozen("fixture", "unit-operator") == result and calls == ["opened"]
    rows[("candidate_freezes", "fixture")]["candidate_hash"] = "changed"
    with pytest.raises(Conflict, match="integrity"): repo.simulate_frozen("fixture", "unit-operator")
    assert calls == ["opened"]
