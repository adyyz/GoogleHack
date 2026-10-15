import pytest

from backend.models import Categorization, Finding, Investigation
from backend.validation import validate_model_output


def test_unknown_sources_and_unsafe_closure_are_rejected():
    evidence = {"evidence_ids": ["source-1"], "missing_context": [], "protected_signals": []}
    finding = Finding(text="Synthetic observation", evidence_ids=["source-1"])
    output = Categorization(primary_typology="LOW_RISK", suggested_action="CLOSE", rationale=finding, uncertainty="LOW")
    assert validate_model_output(output, evidence)["semantic_support"] == "REQUIRES_MANUAL_REVIEW"
    with pytest.raises(ValueError): validate_model_output(output, {**evidence, "missing_context": ["History missing"]})
    with pytest.raises(ValueError): validate_model_output(output, {**evidence, "protected_signals": ["STRUCTURING"]})
    with pytest.raises(ValueError): validate_model_output(output, {**evidence, "evidence_ids": ["different-source"]})


def test_investigation_limit_includes_all_narrative_sections():
    finding = Finding(text="Observation", evidence_ids=["source-1"])
    brief = Investigation(overview=finding, key_findings=[], counter_evidence=[], missing_information=[],
        next_steps=["Review " * 499], limitations=[])
    with pytest.raises(ValueError): validate_model_output(brief, {"evidence_ids": ["source-1"]})
