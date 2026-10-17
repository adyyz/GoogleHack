from collections import Counter
from datetime import timedelta

import pytest
from pydantic import ValidationError

from backend.dataset import generate_dataset
from backend.engine import candidate_options, detect, enrich, prioritize, risk_assessment, simulate
from backend.models import Split, Transaction
from backend.seed import public_cases


def test_public_case_hints_do_not_complete_triage():
    cases = public_cases(generate_dataset())
    assert len(cases) == 12
    assert {case["queue_priority"] for case in cases} <= {"URGENT_REVIEW", "NEEDS_CONTEXT", "STANDARD_REVIEW"}
    for case in cases:
        assert case["queue_reason"]
        assert all(alert["status"] == "PENDING" and not alert.get("priority") for alert in case["alerts"])


def test_frozen_population_and_reference_isolation():
    data = generate_dataset()
    assert len(data.cases) == 112
    assert Counter(c.split for c in data.cases.values()) == {Split.DISCOVERY: 40, Split.SELECTION: 20, Split.HOLDOUT: 40, Split.DEMO: 12}
    assert len({c.customer_id for c in data.cases.values()}) == 112
    assert generate_dataset().manifest_hash == data.manifest_hash
    for case in data.cases.values():
        evidence = enrich(data, case)
        assert "reference_labels" not in evidence
        assert "SUSPICIOUS" not in str(evidence)
        assert detect(data, case) == detect(data, case)


def test_boundaries_future_isolation_and_protected_priority():
    data = generate_dataset()
    case = next(c for c in data.cases.values() if c.split == Split.DEMO and c.scenario_family == "structuring")
    evidence = enrich(data, case)
    assert "STRUCTURING" in evidence["signals"]
    assert prioritize(evidence, risk_assessment(evidence), "CLOSE")["priority"] == "URGENT_REVIEW"
    trigger = data.transactions[case.trigger_transaction_id]
    future = trigger.model_copy(update={"id": "future", "occurred_at": trigger.occurred_at + timedelta(seconds=1), "amount_aud_minor": 99_000_000})
    data.transactions[future.id] = future
    assert enrich(data, case) == evidence
    trigger.amount_aud_minor = 1_000_000
    assert "HIGH_VALUE" not in enrich(data, case)["signals"]
    trigger.amount_aud_minor += 1
    assert "HIGH_VALUE" in enrich(data, case)["signals"]
    with pytest.raises(ValidationError): Transaction.model_validate({**trigger.model_dump(), "amount_aud_minor": 100.5})


def test_unknown_context_is_not_low_risk():
    data = generate_dataset()
    case = next(c for c in data.cases.values() if c.scenario_family == "incomplete_context")
    evidence = enrich(data, case)
    risk = risk_assessment(evidence)
    assert detect(data, case)
    assert risk["overall_score"] is None
    assert prioritize(evidence, risk, "CLOSE")["priority"] == "NEEDS_CONTEXT"


def test_case_level_replay_counts_false_negatives_and_candidates():
    data = generate_dataset()
    for candidate in candidate_options():
        result = simulate(data, candidate, Split.DISCOVERY)
        baseline = result["baseline"]
        assert sum(baseline[k] for k in ["TP", "FP", "TN", "FN"]) == len(result["case_ids"])
        assert baseline["FN"] > 0  # Unalerted suspicious controls are in the denominator.
        assert not result["activation_allowed"]
    threshold = simulate(data, candidate_options()[1], Split.DISCOVERY)
    assert threshold["result"] == "RISK_DETECTED"
    exemption = simulate(data, candidate_options()[2], Split.DISCOVERY)
    assert exemption["benign_alerts_removed"] > 0
    assert not exemption["additional_missed_case_ids"]
    with pytest.raises(ValueError): simulate(data, {"kind": "RUN_GENERATED_CODE"}, Split.DISCOVERY)
