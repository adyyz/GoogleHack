"""In-memory lineage fixtures only; no human verdict or provider output is persisted."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from backend.bulk_analytics import AnalyticsRepository
from backend.bulk_dataset import ID
from backend.dataset import content_hash
from backend.repository import Conflict
from backend.rule_intelligence import matrix


def test_calibration_uses_every_chunk_not_the_three_prompt_examples():
    events = [{"id": f"feedback-{index}", "dataset_id": ID, "provenance": "HUMAN_OPERATOR",
        "alert_id": f"alert-{index}", "triage_run_id": f"run-{index}"} for index in range(9)]
    records = {("feedback_events", row["id"]): row for row in events}
    chunks = []
    for start in range(0, 9, 4):
        refs = [{"id": row["id"], "hash": content_hash(row), "run_id": row["triage_run_id"], "alert_id": row["alert_id"]} for row in events[start:start + 4]]
        ident = content_hash(refs)
        records["bulk_evidence_chunks", ident] = {"references": refs}
        chunks.append({"id": ident, "count": len(refs)})
    records["analytical_snapshots", "snapshot"] = {"body": {"bulk_reference_chunks": chunks, "sample_sizes": {"reviewed_alerts": 9}}}
    repo = SimpleNamespace(get=lambda collection, ident: records.get((collection, ident)), evolution_context=lambda _: {"human_feedback": events[:3]})
    assert AnalyticsRepository.calibration_feedback(repo, "snapshot") == events
    records["feedback_events", events[-1]["id"]] = {**events[-1], "provenance": "SYNTHETIC_REFERENCE"}
    with pytest.raises(Conflict, match="review changed"): AnalyticsRepository.calibration_feedback(repo, "snapshot")
    records["feedback_events", events[-1]["id"]] = events[-1]
    records["bulk_evidence_chunks", chunks[-1]["id"]]["references"].pop()
    with pytest.raises(Conflict, match="chunk changed"): AnalyticsRepository.calibration_feedback(repo, "snapshot")


def test_corpus_matrix_has_nine_rules_and_does_not_count_source_references(monkeypatch):
    from backend import calibration
    cases = [{"id": "case", "customer_id": "person", "split": "CALIBRATION_DISCOVERY"}]
    customers = [{"id": "person", "customer_type": "INDIVIDUAL"}]
    alerts = [{"id": "alert", "rule_id": "HIGH_VALUE", "case_id": "case"}]
    feedback = [{"id": "human", "alert_id": "alert", "case_id": "case", "revision": 1,
        "verdict": "FALSE_POSITIVE", "provenance": "HUMAN_OPERATOR", "machine_label": "AUTO_FP"},
        {"id": "reference", "alert_id": "alert", "case_id": "case", "revision": 2, "verdict": "TRUE_POSITIVE", "provenance": "SYNTHETIC_REFERENCE"}]
    from backend.review_metrics import review_summary
    repo = SimpleNamespace(operational_rows=lambda: (cases, customers, alerts, feedback, []),
        review_statistics=lambda rows: review_summary(*rows), source_alert_counts=lambda: {"HIGH_VALUE": 20},
        active_policy=lambda: {"candidate": None}, list=lambda _: [])
    monkeypatch.setattr(calibration, "active_label_policy", lambda _: {"rules": {rule: {"tp": .25, "fp": .65} for rule in __import__('backend.engine', fromlist=['RULES']).RULES}})
    result = matrix(repo)
    assert len(result["rules"]) == 9
    high = result["rules"][0]
    assert high["reviewed_alerts"] == high["false_positive"] == high["agreed"] == 1
    assert high["alert_count"] == high["machine_distribution"]["NOT_RECORDED"] == 20
    assert high["reviewed_fp_proportion"] == 1 and not high["detector_application_supported"]
    assert all(row["reviewed_alerts"] == 0 for row in result["rules"][1:])


def test_observed_effects_separate_reassessments_and_subsequent_human_reviews(monkeypatch):
    from backend import calibration
    from datetime import datetime, timedelta, timezone
    instant = datetime.now(timezone.utc)
    rows = {"auto_label_candidates": [{"id": "candidate", "rule_id": "HIGH_VALUE", "state": "APPLIED", "applied_at": instant,
        "applied_policy_id": "policy", "after": {"correct_fp_resolutions": 3}, "validation": None}],
        "auto_label_assessments": [{"body": {"candidate_id": "candidate", "alert_id": "reassessed", "restoration": False}}],
        "feedback_events": []}
    repo = SimpleNamespace(list=lambda name: deepcopy(rows[name]), get=lambda *_: {"rule_id": "HIGH_VALUE"},
        page=lambda *_args, **_kwargs: {"items": deepcopy(rows["auto_label_candidates"]), "next_cursor": None})
    monkeypatch.setattr(calibration, "active_label_policy", lambda _: {"revision": 1})
    first = AnalyticsRepository.observed_effects(repo)["items"][0]
    assert first["status"] == "NOT_YET_OBSERVED" and first["reassessed_alerts"] == 1
    rows["feedback_events"] = [{"alert_id": "human", "provenance": "HUMAN_OPERATOR", "auto_label_policy_id": "policy", "submitted_at": instant + timedelta(seconds=1), "verdict": "FALSE_POSITIVE"},
        {"alert_id": "synthetic", "provenance": "SYNTHETIC_REFERENCE", "auto_label_policy_id": "policy", "submitted_at": instant + timedelta(seconds=1)}]
    assert AnalyticsRepository.observed_effects(repo)["items"][0]["false_positive"] == 1


def test_corpus_prompt_keeps_counts_and_omits_uncitable_pattern_references():
    from backend.prompts import evolution_prompt_context
    feedback = [{"id": f"review-{index}", "verdict": "FALSE_POSITIVE", "rule_id": "HIGH_VALUE", "triage_run_id": f"run-{index}"} for index in range(3)]
    patterns = [{"rule_id": "HIGH_VALUE", "typology": f"type-{index}", "support_feedback_ids": [f"review-{value}" for value in range(300)]} for index in range(5)]
    source = {"human_feedback": feedback, "pattern_memory": patterns, "analytical_inputs": {"bulk_reference_chunks": [{"id": "chunk"}],
        "feedback_examples_omitted": 297, "pattern_memory": patterns}}
    original = deepcopy(source)
    context = evolution_prompt_context(source)
    assert source == original
    assert len(context["pattern_memory"]) == 3 and context["selection"]["patterns_omitted"] == 2
    assert context["selection"]["feedback_omitted"] == 297
    assert all(row["support_count"] == 300 and row["support_references_omitted"] == 297 and len(row["support_feedback_ids"]) == 3 for row in context["pattern_memory"])


def test_chunked_candidate_training_is_complete_scoped_and_compact_in_history():
    from backend.calibration import candidate_record, candidate_summary
    training = [{"identity_id": str(index % 5), "feedback_id": str(index)} for index in range(401)]
    records, references = {}, []
    for start in range(0, len(training), 200):
        rows = training[start:start + 200]; ident = content_hash(rows)
        records['auto_label_training_chunks', ident] = {'dataset_id': ID, 'rows': rows}
        references.append({'id': ident, 'count': len(rows)})
    records['auto_label_candidates', 'candidate'] = {'dataset_id': ID, 'training': [], 'training_chunks': references,
        'training_count': 401, 'identity_count': 5, 'training_hash': content_hash(training)}
    def document(collection, ident):
        data = records.get((collection, ident))
        return SimpleNamespace(get=lambda **_: SimpleNamespace(exists=data is not None, id=ident, to_dict=lambda: deepcopy(data)))
    repo = SimpleNamespace(dataset_id=ID, db=SimpleNamespace(collection=lambda name: SimpleNamespace(document=lambda ident: document(name, ident))))
    row = candidate_record(repo, 'candidate')
    assert row['training'] == training and content_hash(row['training']) == row['training_hash']
    summary = candidate_summary(row)
    assert summary['training'] == [] and summary['training_count'] == 401 and summary['identity_count'] == 5
    records['auto_label_training_chunks', references[-1]['id']]['dataset_id'] = 'outside-scope'
    with pytest.raises(Conflict, match='chunk integrity'): candidate_record(repo, 'candidate')


def test_review_trend_points_are_distinct_frozen_cohorts_with_real_denominators():
    from backend.rule_intelligence import review_trends
    body = {'feedback_events': [{'id': 'review', 'hash': 'unchanged'}], 'sample_sizes': {'reviewed_alerts': 1, 'conclusive_reviews': 1},
        'rules': {'HIGH_VALUE': {'conclusive_reviews': 3, 'target_rule_reviews': 1, 'false_positive_reviews': 0, 'reviewed_alert_noise_proportion': 0}}}
    bodies = [body, {**body, 'usage': {'attempts': 2}}, {**body, 'feedback_events': [], 'sample_sizes': {'reviewed_alerts': 0, 'conclusive_reviews': 0}, 'rules': {}}]
    snapshots = {content_hash(value): {'id': content_hash(value), 'dataset_id': ID, 'body': value, 'created_at': '2026-10-18T00:00:00Z'} for value in bodies}
    repo = SimpleNamespace(dataset_id=ID, get=lambda _collection, ident: snapshots[ident], page=lambda *_args, **_kwargs: {
        'items': [{'id': str(index), 'state': 'COMPLETE', 'analytical_snapshot_id': ident} for index, ident in enumerate(snapshots)], 'next_cursor': None})
    result = review_trends(repo)
    assert len(result['items']) == 2
    assert result['items'][0]['reviewed_alert_noise_proportion'] == 0 and result['items'][0]['conclusive_reviews'] == 1
    assert result['items'][0]['rules']['HIGH_VALUE']['conclusive_reviews'] == 1
    assert result['items'][0]['rules']['HIGH_VALUE']['overall_conclusive_reviews'] == 3
    assert result['items'][1]['reviewed_alert_noise_proportion'] is None
    snapshots[next(iter(snapshots))]['body'] = {'changed': True}
    with pytest.raises(Conflict, match='trend inputs'): review_trends(repo)


def test_all_rule_rows_have_plain_language_summaries_without_changing_conditions():
    from backend.rule_intelligence import catalog, RULE_DETAILS
    rows = catalog()
    assert len(rows) == 9 and all(len(row['summary'].split()) >= 8 for row in rows)
    assert all(row['condition'] == RULE_DETAILS[row['id']][1] for row in rows)


def test_admin_corpus_usage_reduces_pages_and_retains_global_daily_controls(monkeypatch):
    from backend import bulk_analytics
    refused = {'state': 'FAILED', 'usage_status': 'NOT_APPLICABLE', 'cost_status': 'NOT_APPLICABLE', 'execution_provenance': 'NOT_SENT', 'attempt_number': 1}
    unknown = {'state': 'UNKNOWN_OUTCOME', 'usage_status': 'UNKNOWN', 'cost_status': 'UNKNOWN', 'execution_provenance': 'UNKNOWN', 'attempt_number': 2, 'duration_ms': 40}
    monkeypatch.setattr(bulk_analytics, 'pages', lambda *_args, **_kwargs: iter([[refused], [unknown]]))
    daily = {'limit': 120, 'live_enabled': False}
    result = bulk_analytics.usage(SimpleNamespace(daily_control=lambda: daily), operator_summary=True)
    assert result['failed_attempts'] == 2 and result['retry_count'] == 1 and result['mean_duration_ms'] == 40
    assert result['daily'] == daily and result['total_tokens'] is None and result['categories'] is None
