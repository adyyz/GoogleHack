"""Validate and optionally import coding-agent opinions into local practice only."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.api_core.exceptions import AlreadyExists
from backend.bulk_dataset import SEEDED_ID, corpus
from backend.config import Settings
from backend.dataset import stable_id
from backend.quick_review import reply_schema
from backend.repository import Conflict, Repository
from backend.seeded_baseline import active

SOURCE = Path(__file__).resolve().parents[1] / 'docs' / 'seeded-baseline-agent-drafts.md'
SOURCE_SHA256 = 'db68f2a40eca2dec96d9646f90d8a113f084150e34cf81da43e2d1280b9630f7'
SOURCE_BASELINE = '4b655701f4eda1f479008e0da1d202f48d7fc29beaa41fb95dd31de61ce71de3'
PROVENANCE = 'LOCAL_AGENT_DRAFT_ADVISORY_NOT_HUMAN'


def import_drafts(repo, source=SOURCE, *, apply=False, allow_equivalent_baseline=False):
    if repo.settings.mode != 'local' or repo.settings.project_id != 'demo-aml-insight':
        raise ValueError('Local demo emulators only')
    selected = active(repo)
    if not selected: raise ValueError('Prepare the baseline first')
    if selected['id'] != SOURCE_BASELINE and not allow_equivalent_baseline:
        raise ValueError('Active baseline differs; use --allow-equivalent-baseline only after compatibility review')
    payload = source.read_bytes()
    # Git may check text out as CRLF on Windows; preserve all content while accepting either line ending.
    if sha256(payload.replace(b'\r\n', b'\n')).hexdigest() != SOURCE_SHA256: raise ValueError('Draft document checksum differs')
    text = payload.decode('utf-8')
    if f'Baseline id: `{SOURCE_BASELINE}`' not in text: raise ValueError('Draft baseline header differs')
    blocks = re.findall(r'```json\r?\n(.*?)\r?\n```', text, re.S)
    if len(blocks) != 1: raise ValueError('Expected one JSON block')
    records = json.loads(blocks[0])
    allowed = {row['case_id'] for row in selected['BASELINE']}
    reserved = {row['case_id'] for row in selected['RESERVED']}
    if not isinstance(records, list) or len(records) != len(allowed): raise ValueError('Draft case count differs')
    seen, planned = set(), []
    # Complete validation precedes every write, including audit writes.
    for row in records:
        if not isinstance(row, dict) or set(row) != {'case_id', 'requires_manual_review', 'alert_mapping', 'reviews'}:
            raise ValueError('Invalid draft record shape')
        ident = row['case_id']
        if ident not in allowed or ident in reserved or ident in seen: raise ValueError('Foreign, reserved or duplicate case')
        seen.add(ident)
        original = corpus().case(ident)
        expected = {(a['id'], a['rule_id']) for a in original['alerts']}
        mapping = row['alert_mapping']
        if (not isinstance(mapping, list) or any(set(a) != {'alert_ref', 'alert_id', 'rule_id'} for a in mapping)
            or len(mapping) != len(expected) or {(a['alert_id'], a['rule_id']) for a in mapping} != expected
            or len({a['alert_ref'] for a in mapping}) != len(mapping)):
            raise ValueError('Draft alert mapping differs from source')
        evidence = original['evidence']
        if type(row['requires_manual_review']) is not bool or row['requires_manual_review'] != bool(evidence['protected_signals'] or evidence['missing_context']):
            raise ValueError('Draft manual-review flag differs')
        reply_schema([{'case_id': ident, 'alerts': mapping, 'evidence': evidence}]).model_validate({'reviews': row['reviews']})
        document_id = stable_id(selected['id'], ident)
        previous = repo.get('seeded_advisory_reviews', document_id)
        if previous and (previous.get('case_id') != ident or previous.get('baseline_id') != selected['id']):
            raise Conflict('Existing review identity mismatch')
        planned.append((document_id, row, previous))
    if seen != allowed: raise ValueError('Incomplete baseline coverage')
    created = 0
    if apply:
        for document_id, row, previous in planned:
            if previous: continue
            try:
                repo.create('seeded_advisory_reviews', document_id, {**row, 'dataset_id': SEEDED_ID,
                    'baseline_id': selected['id'], 'run_id': None, 'step_id': None, 'human_review': False,
                    'provenance': PROVENANCE, 'source_baseline_id': SOURCE_BASELINE, 'source_document_sha256': SOURCE_SHA256})
                created += 1
            except AlreadyExists: pass
        repo.audit('AGENT_DRAFTS_IMPORTED', 'seeded_baselines', selected['id'], 'local-agent-draft-import',
            created=created, source_baseline_id=SOURCE_BASELINE, source_document_sha256=SOURCE_SHA256)
    stored = [r for r in repo.list('seeded_advisory_reviews', SEEDED_ID) if r['baseline_id'] == selected['id']]
    drafted = sum(r['provenance'] == PROVENANCE for r in stored)
    return {'mode': 'apply' if apply else 'dry-run', 'baseline_id': selected['id'], 'source_baseline_id': SOURCE_BASELINE,
        'validated': len(records), 'would_create': sum(not previous for _, _, previous in planned), 'created': created,
        'already_present': sum(bool(previous) for _, _, previous in planned), 'agent_drafted': drafted,
        'gemini': len(stored) - drafted, 'pending': len(allowed) - len(stored)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--allow-equivalent-baseline', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(import_drafts(Repository(Settings.load(), SEEDED_ID), apply=args.apply,
            allow_equivalent_baseline=args.allow_equivalent_baseline)))
    except (ValueError, Conflict, KeyError, TypeError):
        raise SystemExit('Draft validation failed; check baseline compatibility, source checksum and record validation. No unvalidated record was imported.')
