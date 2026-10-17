"""Publication projections use in-memory fixtures, never real model or human records."""
from types import SimpleNamespace
import pytest
from backend.dataset import content_hash
from backend.intelligence_api import PublicationRequest, publication_body
from backend.repository import Conflict


def fixture_repo():
    keys = ('total_cases', 'demo_cases', 'total_alerts', 'reviewed_cases', 'reviewed_alerts',
        'true_positive', 'false_positive', 'inconclusive', 'compared', 'agreed', 'suggestion_unavailable', 'machine_uncertain')
    computed = {key: 0 for key in keys}
    computed['private_notes'] = 'Never publish this'
    body = {'computed_statistics': computed}
    result = {'status': 'INSUFFICIENT_EVIDENCE', 'summary': 'Fixture only', 'conclusive_reviews': 0,
        'target_rule': 'HIGH_VALUE', 'target_rule_reviews': 0, 'candidate_id': None, 'hypothesis': None, 'support_feedback_ids': [], 'limitations': []}
    return SimpleNamespace(evolution_detail=lambda _: {'run': {'state': 'COMPLETE'}, 'result': result,
        'analytical_snapshot_id': content_hash(body)}, list=lambda _: [{'display_name': 'Private Customer'}],
        get=lambda *_: {'body': body}, evolution_context=lambda _: {'evidence_ids': [], 'human_feedback': [],
            'analytical_inputs': {'detector_gate': {'conclusive_reviews': 0, 'target_rule_reviews': 0}}})


def test_publication_allowlist_has_only_aggregates_and_reviewed_summary():
    body = publication_body(fixture_repo(), PublicationRequest(expected_revision=0, report_id='a' * 24,
        executive_summary='No conclusive reviews have been recorded.'))
    assert body['counts']['reviewed_alerts'] == 0
    assert set(body) == {'executive_summary', 'counts', 'scope', 'source_report_id', 'sample_note'}
    assert 'private_notes' not in body['counts'] and 'Never publish this' not in str(body)


@pytest.mark.parametrize('summary', [' ', 'Private Customer was flagged.', 'a' * 24, 'word ' * 121, 'Bearer token'])
def test_publication_rejects_identifiers_private_names_and_unbounded_copy(summary):
    with pytest.raises(ValueError): publication_body(fixture_repo(), PublicationRequest(
        expected_revision=0, report_id='a' * 24, executive_summary=summary))


def test_publication_requires_unchanged_frozen_inputs():
    repo = fixture_repo(); repo.get = lambda *_: {'body': {'changed': True}}
    with pytest.raises(Conflict): publication_body(repo, PublicationRequest(
        expected_revision=0, report_id='a' * 24, executive_summary='Aggregate fixture'))
