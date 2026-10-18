"""Corpus and provenance checks; no model or human decisions are synthesized."""
import json
from collections import Counter
from pathlib import Path
import pytest
from backend.bulk_dataset import Corpus, ID, generate, identity_data
from backend.dataset import DATASET_ID, generate_dataset
from backend.engine import RULES, auto_label, enrich, risk_assessment
from backend.bulk_api import Selection, Start
from backend.repository import Repository


@pytest.fixture(scope="module")
def bulk(tmp_path_factory):
    root = tmp_path_factory.mktemp("bulk-corpus")
    generate(root)
    return Corpus(root)


def test_exact_frozen_corpus_and_reference_partition_counts(bulk):
    assert bulk.summary()["transactions"] == 40000 and bulk.summary()["identities"] == 500
    with bulk.connect() as db, bulk.connect(True) as refs:
        assert dict(db.execute("SELECT partition,count(*) FROM cases GROUP BY partition").fetchall()) == {"TRAIN": 16000, "VALIDATION": 4000, "PENDING": 20000}
        assert dict(refs.execute("SELECT partition,count(*) FROM annotations GROUP BY partition").fetchall()) == {"TRAIN": 16000, "VALIDATION": 4000}
        assert db.execute("SELECT count(DISTINCT identity_id) FROM cases").fetchone()[0] == 500
        assert dict(db.execute("SELECT customer_type,count(DISTINCT identity_id) FROM cases GROUP BY customer_type").fetchall()) == {"INDIVIDUAL": 300, "ORGANIZATION": 200}
    assert set(bulk.manifest["rule_alerts"]) == set(RULES) and all(bulk.manifest["rule_alerts"].values())
    groups = [{p["identity_id"] for p in bulk.manifest["partitions"] if p["partition"] == kind} for kind in ("TRAIN", "VALIDATION", "PENDING")]
    assert not any(groups[a] & groups[b] for a, b in ((0, 1), (0, 2), (1, 2)))
    assert generate(bulk.root) == bulk.manifest
    assert DATASET_ID != ID and generate_dataset().manifest_hash == "9f297c1dd06ef395d9dad851348d15c5ffa4db95cedb49dc4ad7b5b36130dfa0"


def test_history_linkage_and_reference_denial(bulk):
    row = bulk.page(limit=1)["items"][0]
    case = bulk.case(row["id"])
    assert case["evidence"]["customer"]["id"] == row["identity_id"]
    assert all(tx["occurred_at"] < case["evidence"]["trigger"]["occurred_at"] for tx in case["evidence"]["history"])
    assert "reference" not in json.dumps(case).lower() and "verdict" not in json.dumps(case).lower()
    with bulk.connect() as db: reserved = db.execute("SELECT id FROM cases WHERE partition='VALIDATION' LIMIT 1").fetchone()[0]
    with pytest.raises(LookupError): bulk.case(reserved)
    with pytest.raises(ValueError): bulk.page(partition="VALIDATION")
    with pytest.raises(ValueError): bulk.page(limit=101)
    with pytest.raises(ValueError): Repository.__init__(object.__new__(Repository), None, "arbitrary-dataset")


def test_pagination_filters_and_independent_annotations(bulk):
    first = bulk.page(limit=50, customer_type="INDIVIDUAL", rule="HIGH_VALUE")
    second = bulk.page(limit=50, cursor=first["next_cursor"], customer_type="INDIVIDUAL", rule="HIGH_VALUE")
    assert first["total"] == second["total"] > 100
    assert not {r["id"] for r in first["items"]} & {r["id"] for r in second["items"]}
    assert all(r["customer_type"] == "INDIVIDUAL" and "HIGH_VALUE" in r["rules"] for r in first["items"])
    assert bulk.page(query="no such fictional identity")["total"] == 0
    rows = bulk.observations("TRAIN")
    assert rows and all(r["provenance"] == "SYNTHETIC_REFERENCE" for r in rows)
    # Independent labels include disagreements for the same heuristic value.
    assert any(len({r["verdict"] for r in rows if r["score"] == score}) > 1 for score in {r["score"] for r in rows})


def test_batch_validation_and_protected_heuristic_compatibility():
    for ids in ([], ["a" * 24] * 101):
        with pytest.raises(ValueError): Selection(case_ids=ids)
    with pytest.raises(ValueError): Selection(case_ids=["../case"])
    data, _ = identity_data(250)
    case = next(iter(data.cases.values())); evidence = enrich(data, case)
    classification = {"primary_typology": "LOW_RISK", "suggested_action": "CLOSE", "uncertainty": "HIGH"}
    result = auto_label(evidence, classification)
    assert result["heuristic_score"] == 1 and result["score_is_probability"] is False
    assert auto_label({**evidence, "protected_signals": ["STRUCTURING"]}, classification)["predicted_verdict"] == "AUTO_UNCERTAIN"


def test_bulk_accounting_reduces_more_than_ten_thousand_rows_without_inventing_categories(monkeypatch):
    from backend import bulk_analytics
    row = {"state": "SUCCEEDED", "usage_status": "PROVIDER_REPORTED", "cost_status": "UNKNOWN", "total_tokens": 15,
        "prompt_tokens": 10, "candidate_tokens": 5, "cached_prompt_tokens": None, "thought_tokens": None, "tool_prompt_tokens": None}
    monkeypatch.setattr(bulk_analytics, "pages", lambda *_args, **_kwargs: iter([[row] * 500 for _ in range(25)]))
    result = bulk_analytics.usage(None)
    assert result["ledger_rows"] == 12500 and result["total_tokens"] == 187500
    assert result["provider_attempts"] == 12500 and result["unknown_attempts"] == 12500
    assert result["categories"] is None and result["known_categories"]["cached_prompt_tokens"] is None


def test_python_browser_cutoff_parity():
    import subprocess
    from backend.calibration import GRID, classify
    fixtures = []
    for tp in GRID:
        for fp in GRID:
            if tp >= fp: continue
            for score in sorted(set([0, .2, .3, .5, .7, .8, 1, tp, fp, max(0, fp-.001), min(1, tp+.001)])):
                for forced in (True, False):
                    fixtures.append({"inputs": [score, forced, tp, fp], "expected": "AUTO_UNCERTAIN" if forced else classify(score, {"tp": tp, "fp": fp})})
    result = subprocess.run(["node", "scripts/check-bulk-label.cjs"], input=json.dumps(fixtures), text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
