"""Reference walkthroughs are synthetic, disjoint from operational and sealed cohorts."""
import json
from backend import bulk_reference as reference
from backend.bulk_dataset import corpus
from backend.engine import RULES


def test_preload_is_exact_reproducible_balanced_and_never_human_or_provider_evidence():
    rows, summary = reference.cohort(), reference.summary()
    assert len(rows) == len({r['id'] for r in rows}) == 10000
    assert summary['population_fraction'] == .25 and summary['human_reviews'] == summary['provider_calls'] == 0
    assert set(r['rule_id'] for r in summary['rules']) == set(RULES)
    assert all(r['cases'] > 0 and r['balancing_cases'] > 0 for r in summary['rules'])
    assert sum(r['balancing_cases'] for r in summary['rules']) == 10000
    assert sum(summary['identity_types'].values()) == 10000
    assert summary['metrics']['true_positive'] + summary['metrics']['false_positive'] + summary['metrics']['inconclusive'] == 10000
    assert all(r['partition'] == 'TRAIN' and r['provenance'] == reference.PROVENANCE for r in rows)
    assert all(r['reference_prediction'] == 'AUTO_UNCERTAIN' for r in rows if r['requires_review'])
    before = summary['cohort_hash']
    reference.cohort.cache_clear(); reference.summary.cache_clear()
    assert reference.summary()['cohort_hash'] == before


def test_reference_and_operational_queue_merge_filters_and_cursor_do_not_skip_or_duplicate():
    data = corpus()
    first = reference.merge(data.page(limit=50), limit=50)
    second = reference.merge(data.page(limit=50, cursor=first['next_cursor']), limit=50, cursor=first['next_cursor'])
    assert first['total'] == second['total'] == 30000
    assert not {r['id'] for r in first['items']} & {r['id'] for r in second['items']}
    assert all(r['reference'] for r in first['items'])
    last_reference = reference.cohort()[-1]['ordinal']
    transition = reference.merge(data.page(limit=50, cursor=last_reference-1), limit=50, cursor=last_reference-1)
    assert transition['items'][0]['reference'] and transition['items'][1]['partition'] == 'PENDING'
    filtered = reference.page(customer_type='ORGANIZATION', rule='PEP')
    assert filtered['total'] > 0 and all(r['customer_type'] == 'ORGANIZATION' and 'PEP' in r['rules'] for r in filtered['items'])
    assert reference.page(query='no matching identity')['total'] == 0
