"""Pure malformed-link fixtures; no model output or feedback is persisted."""
from types import SimpleNamespace

import pytest

from backend.dataset import DATASET_ID
from backend.repository import Conflict, Repository


def test_private_reads_refuse_foreign_linked_records():
    repo = object.__new__(Repository)
    rows = {("pipeline_runs", "parent"): {"id": "parent", "dataset_id": DATASET_ID, "child_run_ids": ["child"]},
        ("pipeline_runs", "child"): {"id": "child", "dataset_id": "foreign", "parent_run_id": "parent"},
        ("alerts", "alert"): {"id": "alert", "dataset_id": DATASET_ID, "latest_run_id": "child"}}
    repo.get = lambda collection, ident: rows.get((collection, ident))
    with pytest.raises(Conflict, match="Child run linkage"): repo.run_detail("parent")
    with pytest.raises(Conflict, match="Latest run linkage"): repo.alert_detail("alert")
    rows[("pipeline_runs", "child")].update(dataset_id=DATASET_ID, parent_run_id="another-parent")
    with pytest.raises(Conflict, match="Child run linkage"): repo.run_detail("parent")


def test_cursor_must_match_requested_filters():
    repo = object.__new__(Repository)
    cursor = SimpleNamespace(exists=True, to_dict=lambda: {"alert_id": "other-alert", "revision": 1})
    query = SimpleNamespace()
    query.where = lambda **_kwargs: query
    query.order_by = lambda *_args, **_kwargs: query
    query.document = lambda _ident: SimpleNamespace(get=lambda **_kwargs: cursor)
    repo.db = SimpleNamespace(collection=lambda _name: query)
    with pytest.raises(Conflict, match="does not belong"):
        repo.page("feedback_events", 50, "foreign-cursor", [("alert_id", "selected-alert")], order="revision")


def test_retry_read_requires_original_rejection_and_matching_links():
    from backend.dataset import stable_id
    from backend.repository import now
    repo = object.__new__(Repository)
    run = {"id": "unit-run", "dataset_id": DATASET_ID, "config_bundle_id": "unit-bundle"}
    first_id, second_id = [stable_id(run["id"], "A5", number) for number in [1, 2]]
    first = {"id": first_id, "run_id": run["id"], "dataset_id": DATASET_ID, "config_bundle_id": "unit-bundle",
        "leg_id": "A5", "attempt_number": 1, "state": "FAILED", "output": None, "finished_at": now(),
        "execution_provenance": "REAL_PROVIDER", "error_code": "PROVIDER_HTTP_429", "retry_delay_seconds": 1}
    second = {**first, "id": second_id, "attempt_number": 2, "retry_of_step_id": first_id}
    rows = {first_id: first, second_id: second}
    def document(ident):
        return SimpleNamespace(get=lambda **_kwargs: SimpleNamespace(id=ident, exists=ident in rows, to_dict=lambda: rows.get(ident)))
    repo.db = SimpleNamespace(collection=lambda _name: SimpleNamespace(document=document))
    assert repo._leg_step(None, run, "A5") == second
    second["retry_of_step_id"] = "another-attempt"
    with pytest.raises(Conflict, match="retry chain"): repo._leg_step(None, run, "A5")
    first["run_id"] = "another-run"
    with pytest.raises(Conflict, match="step linkage"): repo._leg_step(None, run, "A5")
