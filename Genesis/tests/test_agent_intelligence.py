from copy import deepcopy
import pytest
from backend.agent_views import advisory_view, agent_trace
from backend.models import RiskExplanation, Categorization, Finding
from backend.validation import validate_model_output


def test_advisory_is_separate_and_missing_dimensions_never_become_zero():
    risk = {"overall_score": .1}
    output = {"advisory_dimensions": {key: .8 for key in ("transaction", "customer", "account", "behavioral", "network")}}
    before = deepcopy(output)
    assert advisory_view(output, risk)["overall_score"] == .8
    assert advisory_view(output, risk)["large_difference"]
    assert output == before and risk == {"overall_score": .1}
    output["advisory_dimensions"]["network"] = None
    assert advisory_view(output, risk)["overall_score"] is None
    evidence = {"evidence_ids": [], "missing_context": ["incomplete"]}
    with pytest.raises(ValueError):
        validate_model_output(RiskExplanation(findings=[], counter_evidence=[], limitations=[], **output), evidence)


def test_trace_does_not_promote_failed_unknown_or_unstarted_stages():
    rows = [{"run_id": "r", "leg_id": "A2", "state": "FAILED", "output": {"invalid": True}},
        {"run_id": "r", "leg_id": "A3", "state": "UNKNOWN_OUTCOME", "output": {"invalid": True}}]
    trace = {row["leg_id"]: row for row in agent_trace(rows, "r")}
    assert trace["A2"]["state"] == "FAILED" and trace["A2"]["output"] is None
    assert trace["A3"]["state"] == "UNKNOWN_OUTCOME" and trace["A3"]["output"] is None
    assert trace["A4"]["state"] == "NOT_STARTED"


def test_secondary_typologies_require_distinct_supported_citations():
    finding = Finding(text="Evidence", evidence_ids=["source"])
    output = Categorization(primary_typology="OTHER", suggested_action="REVIEW", rationale=finding,
        uncertainty="MEDIUM", secondary_typologies=[{"typology": "LAYERING", "rationale": finding}])
    evidence = {"evidence_ids": ["source"], "missing_context": [], "protected_signals": []}
    assert validate_model_output(output, evidence)["citation_count"] == 2
    with pytest.raises(ValueError): validate_model_output(output, {**evidence, "evidence_ids": []})


def test_new_generation_requires_advisory_but_historical_output_remains_readable():
    historical = RiskExplanation(findings=[], counter_evidence=[], limitations=[])
    evidence = {"evidence_ids": [], "missing_context": [], "protected_signals": []}
    assert validate_model_output(historical, evidence)["citation_id_validity"]
    with pytest.raises(ValueError, match="Versioned risk"):
        validate_model_output(historical, {**evidence, "intelligence_version": 2})


def test_cross_rule_report_can_explain_fp_without_authorizing_detector_changes():
    from backend.models import EvolutionAssessment
    result = EvolutionAssessment(status="INSUFFICIENT_EVIDENCE", report_version=2, conclusive_reviews=1,
        target_rule_reviews=0, target_rule="HIGH_VALUE", summary="Fixture only", limitations=[],
        findings=[{"rule_id": "CRYPTO", "title": "Fixture", "explanation": "A hypothesis, not a measured improvement",
            "support_feedback_ids": ["feedback"], "signal_codes": ["CRYPTO"]}],
        recommendation_items=[{"rule_id": "CRYPTO", "title": "Inspect evidence", "rationale": "Fixture only",
            "support_feedback_ids": ["feedback"], "kind": "INFORMATIONAL"}])
    evidence = {"evidence_ids": ["feedback"], "analytical_inputs": {"detector_gate": {
        "conclusive_reviews": 1, "target_rule_reviews": 0}, "computed_statistics": {"signal_codes": ["CRYPTO"]}},
        "human_feedback": [{"id": "feedback", "rule_id": "CRYPTO", "verdict": "FALSE_POSITIVE"}], "intelligence_version": 2}
    assert validate_model_output(result, evidence)["citation_id_validity"]
    executable = result.model_copy(deep=True); executable.recommendation_items[0].kind = "DETECTOR_CHANGE"
    with pytest.raises(ValueError, match="HIGH_VALUE"): validate_model_output(executable, evidence)
    with pytest.raises(ValueError, match="false-positive support"):
        validate_model_output(result, {**evidence, "human_feedback": [{"id": "feedback", "rule_id": "CRYPTO", "verdict": "TRUE_POSITIVE"}]})
