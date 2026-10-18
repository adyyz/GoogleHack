from hashlib import sha256
import json
from types import SimpleNamespace

import pytest
from scripts import import_agent_drafts as importer
from backend.dataset import stable_id


@pytest.fixture
def setup_drafts(tmp_path, monkeypatch):
    source = importer.SOURCE.read_text(encoding='utf-8')
    rows = json.loads(source.split('```json\n', 1)[1].split('\n```', 1)[0])[:2]
    selected = {'id': 'TEST_ONLY_ACTIVE', 'BASELINE': [{'case_id': r['case_id']} for r in rows], 'RESERVED': [{'case_id': 'reserved-test-only'}]}
    monkeypatch.setattr(importer, 'active', lambda _repo: selected)
    path = tmp_path / 'test-only.md'
    writes, stored = [], {}
    def write_source(records):
        path.write_text(f'Baseline id: `{importer.SOURCE_BASELINE}`\n```json\n{json.dumps(records)}\n```', encoding='utf-8')
        monkeypatch.setattr(importer, 'SOURCE_SHA256', sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest())
    def create(collection, ident, body):
        assert collection == 'seeded_advisory_reviews'
        writes.append(ident); stored[ident] = body
    repo = SimpleNamespace(settings=SimpleNamespace(mode='local', project_id='demo-aml-insight'),
        get=lambda _collection, ident: stored.get(ident), create=create, audit=lambda *args, **kwargs: None,
        list=lambda *_args: list(stored.values()))
    write_source(rows)
    return repo, path, rows, selected, writes, stored, write_source


def test_import_preserves_existing_gemini_is_dry_by_default_and_idempotent(setup_drafts):
    repo, path, rows, selected, writes, stored, _ = setup_drafts
    ident = stable_id(selected['id'], rows[0]['case_id'])
    original = {'case_id': rows[0]['case_id'], 'baseline_id': selected['id'], 'provenance': 'REAL_PROVIDER_AI_ADVISORY_NOT_HUMAN', 'run_id': 'TEST_ONLY_EXISTING'}
    stored[ident] = original.copy()
    with pytest.raises(ValueError): importer.import_drafts(repo, path)
    result = importer.import_drafts(repo, path, allow_equivalent_baseline=True)
    assert result['would_create'] == 1 and not writes
    result = importer.import_drafts(repo, path, apply=True, allow_equivalent_baseline=True)
    assert result['created'] == result['agent_drafted'] == result['gemini'] == 1 and result['pending'] == 0
    assert stored[ident] == original
    assert all(r.get('run_id') is None and r.get('step_id') is None and not r['human_review'] for r in stored.values() if r['provenance'] == importer.PROVENANCE)
    assert importer.import_drafts(repo, path, apply=True, allow_equivalent_baseline=True)['created'] == 0


@pytest.mark.parametrize('fault', ['citation', 'reserved', 'duplicate', 'mapping', 'manual'])
def test_last_invalid_record_prevents_all_writes(setup_drafts, fault):
    repo, path, rows, selected, writes, _, write_source = setup_drafts
    if fault == 'citation': rows[-1]['reviews'][0]['evidence_ids'] = ['invented-test-only']
    if fault == 'reserved': rows[-1]['case_id'] = selected['RESERVED'][0]['case_id']
    if fault == 'duplicate': rows[-1] = rows[0]
    if fault == 'mapping': rows[-1]['alert_mapping'][0]['rule_id'] = 'WRONG_TEST_ONLY'
    if fault == 'manual': rows[-1]['requires_manual_review'] = not rows[-1]['requires_manual_review']
    write_source(rows)
    with pytest.raises(ValueError): importer.import_drafts(repo, path, apply=True, allow_equivalent_baseline=True)
    assert not writes
