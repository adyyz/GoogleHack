"""Algorithm fixtures only; none is stored as human or provider evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import pytest
from backend.calibration import METHOD, fit, measured, safe_benefit, check_candidate
from backend.dataset import content_hash
from backend.repository import Conflict
from backend.rule_intelligence import catalog, statistics


def observations():
    return [{"identity_id": str(index), "feedback_id": str(index), "score": .5 if index < 8 else .8 if index < 12 else .2,
        "verdict": "FALSE_POSITIVE" if index < 12 else "TRUE_POSITIVE"} for index in range(15)]


def test_calibration_requires_counts_diversity_and_safe_measured_fp_resolution():
    rows = observations(); baseline = {"tp": .25, "fp": .65, "cohort": None}
    assert fit(rows, baseline, 29) is None and fit(rows[:14], baseline, 30) is None
    collapsed = [{**row, "identity_id": 'one-' + row["verdict"]} for row in rows]
    assert fit(collapsed, baseline, 30) is None
    before = deepcopy(rows); result = fit(rows, baseline, 30)
    assert result == fit(rows, baseline, 30) and rows == before
    assert result["thresholds"] == {"tp": .25, "fp": .4, "cohort": None}
    assert result["after"]["correct_fp_resolutions"] == 8 and result["after"]["wrong_fp"] == 0
    assert fit([{**row, "score": .5} for row in rows], baseline, 30) is None


def test_forward_validation_integrity_and_no_identity_overlap():
    training = observations(); frozen = datetime.now(timezone.utc); baseline = {"tp": .25, "fp": .65, "cohort": None}
    fitted = fit(training, baseline, 30)
    row = {"rule_id": "HIGH_VALUE", "method": METHOD, "cohort": "cohort", "baseline": baseline,
        "thresholds": {**fitted["thresholds"], "cohort": "cohort"}, "training": training,
        "training_hash": content_hash(training), "frozen_at": frozen, "validation": None}
    row["candidate_hash"] = content_hash({key: row[key] for key in ("rule_id", "thresholds", "training_hash", "cohort", "method", "baseline", "frozen_at")})
    forward = [{**value, "identity_id": 'future-' + str(index), "submitted_at": frozen + timedelta(seconds=1), "cohort": "cohort"}
        for index, value in enumerate([training[0], training[1], training[13], training[14], training[8]])]
    before = measured(forward, baseline, baseline); after = measured(forward, row["thresholds"], baseline)
    row["validation"] = {"rows": forward, "content_hash": content_hash(forward), "before": before, "after": after, "passed": safe_benefit(after, before), "provenance": "PROSPECTIVE_HUMAN_REVIEWS"}
    check_candidate(row)
    tampered = deepcopy(row); tampered["thresholds"]["fp"] = .3
    with pytest.raises(Conflict): check_candidate(tampered)
    tampered = deepcopy(row); tampered["validation"]["rows"][0]["identity_id"] = training[0]["identity_id"]
    tampered["validation"]["content_hash"] = content_hash(tampered["validation"]["rows"])
    with pytest.raises(Conflict): check_candidate(tampered)


def test_all_nine_rules_and_overlapping_statistics_keep_human_denominators():
    assert len(catalog()) == 9 and len({row['id'] for row in catalog()}) == 9
    assert {row['id'] for row in catalog() if row['protected']} == {'POST_DEATH', 'STRUCTURING'}
    cases = [{"id": "case", "customer_id": "person", "split": "DEMO"}]
    customers = [{"id": "person", "customer_type": "INDIVIDUAL"}, {"id": "outside", "customer_type": "ORGANIZATION"}]
    alerts = [{"id": "alert", "case_id": "case", "rule_id": "HIGH_VALUE"}]
    feedback = [{"id": "feedback", "alert_id": "alert", "case_id": "case", "triage_run_id": "run", "revision": 1,
        "verdict": "FALSE_POSITIVE", "provenance": "HUMAN_OPERATOR", "machine_label": "AUTO_FP"}]
    validation = {"schema_pass": True, "evidence_pass": True}
    steps = [{"run_id": "run", "leg_id": "A1", "state": "SUCCEEDED", "execution_provenance": "DETERMINISTIC",
        "output": {"signals": ["HIGH_VALUE", "NEW_ACCOUNT"], "missing_context": []}},
        {"run_id": "run", "leg_id": "A3", "state": "SUCCEEDED", "execution_provenance": "REAL_PROVIDER", "validation": validation,
         "output": {"primary_typology": "OTHER", "secondary_typologies": [{"typology": "LAYERING"}]}}]
    result = statistics(cases, customers, alerts, feedback, steps)
    assert result['false_positive'] == result['reviewed_alerts'] == result['total_identities'] == 1
    assert len(result['groups']['signal']) == 2 and result['groups']['secondary_typology'][0]['false_positive'] == 1
    assert result['compared'] == result['agreed'] == 1 and result['population_fpr'] is None


def test_calibration_deduplicates_alerts_and_hashes_original_feedback(monkeypatch):
    from types import SimpleNamespace
    from backend import calibration
    original = {"id": "feedback", "dataset_id": "TEST_ONLY", "case_id": "case", "alert_id": "alert", "revision": 2, "provenance": "HUMAN_OPERATOR",
        "verdict": "TRUE_POSITIVE", "triage_run_id": "run", "submitted_at": datetime.now(timezone.utc)}
    records = {('feedback_events', 'feedback'): original, ('alerts', 'alert'): {"id": "alert", "dataset_id": "TEST_ONLY", "case_id": "case", "rule_id": "HIGH_VALUE"},
        ('pipeline_runs', 'run'): {"id": "run", "dataset_id": "TEST_ONLY", "case_id": "case", "state": "COMPLETE", "alert_id": "alert", "config_bundle_id": "bundle"},
        ('config_versions', 'bundle'): {"body": {}}}
    repo = SimpleNamespace(dataset_id="TEST_ONLY", get=lambda collection, ident: records[(collection, ident)],
        operational_case=lambda _: {"customer_id": "identity"}, db=SimpleNamespace(transaction=lambda **_: None),
        _sealed_chain=lambda *_: [{"leg_id": "A0", "output": {"heuristic_score": .5,
            "requires_context_or_protected_review": False, "score_is_probability": False}}])
    monkeypatch.setattr(calibration.firestore, 'transactional', lambda operation: operation)
    rows = calibration.observations(repo, [{**original, "revision": 1}, {**original, "rule_id": "HIGH_VALUE"}])
    assert len(rows) == 1 and rows[0]['feedback_hash'] == content_hash(original)
