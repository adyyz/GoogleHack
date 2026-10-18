"""Transport faults and invalid test JSON never become successful model output."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.config import Settings
from backend.dataset import DATASET_ID, stable_id
from backend.gateway import generate_json
from backend.gemini_smoke import SmokeReply
from backend.models import StepRun


class FakeRepo:
    def __init__(self, settings):
        self.settings = settings
        self.reservations = []
        self.writes = []
        self.db = self

    def reserve_model_attempt(self, step):
        self.reservations.append(step)
        return True

    def seal_provider_attempt(self, _step, data):
        self.writes.append(data)
        return True

    def daily_control(self): return {"live_enabled": True}
    def get(self, _collection, _ident): return None

    def collection(self, _name): return self
    def document(self, _ident): return self
    def update(self, data): self.writes.append(data)


def setup(monkeypatch, *, count=50, error=None, text='{"status":"INVALID_TEST_RESULT"}'):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-credential")
    settings = replace(Settings.load(), local_gemini_enabled=True, local_gemini_free_verified=True,
        local_gemini_verified_until=datetime.now(timezone.utc) + timedelta(hours=1))
    repo = FakeRepo(settings)
    calls = []

    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        @property
        def models(self): return self
        def count_tokens(self, **kwargs):
            calls.append(("count", kwargs))
            return SimpleNamespace(total_tokens=count)
        def generate_content(self, **kwargs):
            calls.append(("generate", kwargs))
            if error: raise error
            return SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=50, candidates_token_count=5,
                total_token_count=55), text=text, response_id="test-request")

    monkeypatch.setattr("backend.gateway._provider_client", lambda _settings: Client())
    step = StepRun(id=stable_id("test-run", "EVALUATE", 1), dataset_id=DATASET_ID, run_id="test-run",
        leg_id="EVALUATE", config_bundle_id="test-bundle", state="STARTED", started_at=datetime.now(timezone.utc),
        input_hash="test-input", model_id=settings.active_model_id, usage_status="UNKNOWN", cost_status="UNKNOWN")
    return repo, step, calls


def test_closed_gate_and_oversize_precount_never_generate(monkeypatch):
    repo, step, calls = setup(monkeypatch, count=513)
    result = generate_json(repo, step, "Test prompt", SmokeReply, input_limit=512, output_limit=128)
    assert result.error_code == "CONTEXT_LIMIT"
    assert not repo.reservations and not repo.writes
    assert [kind for kind, _ in calls] == ["count"]
    repo.settings = replace(repo.settings, local_gemini_enabled=False)
    calls.clear()
    assert generate_json(repo, step, "Test", SmokeReply, input_limit=512, output_limit=128).outcome == "NOT_SENT"
    assert calls == []


def test_structured_evaluation_is_pinned_and_validated(monkeypatch):
    repo, step, calls = setup(monkeypatch, text='{"status":"OK"}')
    repo.get = lambda *_args: {'body': {'structured_output': True}}
    result = generate_json(repo, step, 'Test prompt', SmokeReply, input_limit=512, output_limit=128, structured_output=True)
    assert result.outcome == 'SUCCEEDED'
    assert calls[1][1]['config']['response_json_schema'] == SmokeReply.model_json_schema()
    assert repo.reservations[0].input_snapshot['generation_config']['response_json_schema'] == SmokeReply.model_json_schema()


def test_invalid_output_is_not_stored_as_model_output(monkeypatch):
    repo, step, calls = setup(monkeypatch)
    result = generate_json(repo, step, "Test prompt", SmokeReply, input_limit=512, output_limit=128)
    assert result.error_code == "OUTPUT_INVALID" and result.output is None
    assert repo.writes[0]["state"] == "FAILED" and repo.writes[0]["output"] is None
    assert repo.writes[0]["total_tokens"] == 55
    assert calls[0][1]["contents"] == calls[1][1]["contents"]
    assert calls[1][1]["config"]["max_output_tokens"] == 128
    assert len(repo.reservations) == 1


@pytest.mark.parametrize("status,state", [(401, "FAILED"), (429, "FAILED"), (503, "UNKNOWN_OUTCOME"), (None, "UNKNOWN_OUTCOME")])
def test_provider_fault_is_redacted_and_never_retried(monkeypatch, status, state):
    failure = RuntimeError("DO_NOT_STORE_this_key_or_prompt")
    failure.code = status
    repo, step, calls = setup(monkeypatch, error=failure)
    result = generate_json(repo, step, "Test prompt", SmokeReply, input_limit=512, output_limit=128)
    assert result.outcome == state
    assert repo.writes[0]["output"] is None and repo.writes[0]["state"] == state
    assert "DO_NOT_STORE" not in str(repo.writes) + str(result)
    assert [kind for kind, _ in calls] == ["count", "generate"]


def test_grounding_rejects_unknown_citations_before_success_is_stored(monkeypatch):
    from backend.models import Categorization
    repo, step, calls = setup(monkeypatch, text='{"primary_typology":"OTHER","suggested_action":"REVIEW","rationale":{"text":"Test fixture only","evidence_ids":["unsupplied-id"]},"uncertainty":"HIGH"}')
    step = step.model_copy(update={"leg_id": "A3"})
    result = generate_json(repo, step, "Test", Categorization, input_limit=2048, output_limit=768,
        evidence={"evidence_ids": ["source-id"], "missing_context": [], "protected_signals": []})
    assert result.error_code == "OUTPUT_INVALID"
    assert repo.writes[0]["state"] == "FAILED" and repo.writes[0]["output"] is None
    assert not any(write["state"] == "SUCCEEDED" for write in repo.writes)


def test_kill_switch_prevents_even_token_precount(monkeypatch):
    repo, step, calls = setup(monkeypatch)
    repo.daily_control = lambda: {"live_enabled": False}
    result = generate_json(repo, step, "Test", SmokeReply, input_limit=512, output_limit=128)
    assert result.error_code == "LIVE_AI_DISABLED"
    assert calls == [] and repo.reservations == [] and repo.writes == []


def test_a5_invented_counts_never_become_successful_model_output(monkeypatch):
    from backend.models import EvolutionAssessment
    from backend.evolution import sufficiency
    repo, step, calls = setup(monkeypatch, text='{"status":"INSUFFICIENT_EVIDENCE","conclusive_reviews":30,"target_rule_reviews":15,"target_rule":"HIGH_VALUE","summary":"Invalid fixture","limitations":[]}')
    step = step.model_copy(update={"leg_id": "A5"})
    result = generate_json(repo, step, "Test", EvolutionAssessment, input_limit=8192, output_limit=3072,
        evidence={"evidence_ids": [], "analytical_inputs": {"detector_gate": sufficiency(0, 0)}, "human_feedback": []})
    assert result.error_code == "OUTPUT_INVALID" and result.output is None
    assert repo.writes[0]["state"] == "FAILED" and repo.writes[0]["output"] is None
    assert calls[1][1]["config"]["max_output_tokens"] == 3072


@pytest.mark.parametrize("response", ['{"status":"OK"}', '{"status":"INVALID_TEST_RESULT"}'])
def test_late_response_does_not_reopen_a_sealed_attempt(monkeypatch, response):
    repo, step, _calls = setup(monkeypatch, text=response)
    repo.seal_provider_attempt = lambda _step, _changes: False
    result = generate_json(repo, step, "Late response fixture", SmokeReply, input_limit=512, output_limit=128)
    assert result.outcome == "UNKNOWN_OUTCOME" and result.error_code == "ATTEMPT_ALREADY_SEALED"
    assert result.output is None and repo.writes == []


def test_expired_execution_budget_blocks_token_precount(monkeypatch):
    from backend.models import WorkerLease
    from backend.repository import Conflict
    repo, step, calls = setup(monkeypatch)
    instant = datetime.now(timezone.utc)
    step = step.model_copy(update={"worker_lease": WorkerLease(run_id=step.run_id, generation=1, owner="fixture",
        expires_at=instant + timedelta(seconds=300), execution_deadline_at=instant + timedelta(seconds=240))})
    def reject(_lease, reserve_seconds):
        assert reserve_seconds == 65
        raise Conflict("WORKER_EXECUTION_BOUND")
    repo.check_worker_lease = reject
    result = generate_json(repo, step, "Test", SmokeReply, input_limit=512, output_limit=128)
    assert result.outcome == "NOT_SENT" and result.error_code == "WORKER_EXECUTION_BOUND"
    assert calls == [] and repo.reservations == [] and repo.writes == []


def test_only_explicit_short_nonquota_rejection_records_retry_permission(monkeypatch):
    from google.genai.errors import ClientError
    from backend.gateway import _retry_delay
    info = {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "1s"}
    def failure(details, code=429):
        return ClientError(code, {"error": {"status": "RESOURCE_EXHAUSTED", "details": details, "message": "private error"}})
    assert _retry_delay(failure([info])) == 1
    for details in [[], [info, {"@type": "type.googleapis.com/google.rpc.QuotaFailure"}],
        [{**info, "retryDelay": "6s"}], [{**info, "retryDelay": "NaNs"}], [{**info, "retryDelay": "-1s"}]]:
        assert _retry_delay(failure(details)) is None
    assert _retry_delay(failure([info], 403)) is None
    repo, step, calls = setup(monkeypatch, error=failure([info]))
    result = generate_json(repo, step, "Test", SmokeReply, input_limit=512, output_limit=128)
    assert result.outcome == "FAILED" and repo.writes[0]["retry_delay_seconds"] == 1
    assert repo.writes[0]["output"] is None and "private error" not in str(repo.writes)
    assert [kind for kind, _ in calls] == ["count", "generate"]  # Worker owns the single retry.


def test_cloud_transport_refuses_unverified_tuple_and_requires_worker_lease(monkeypatch):
    from backend.models import WorkerLease
    repo, step, calls = setup(monkeypatch)
    settings = replace(repo.settings, mode="cloud", project_id="unit-project", firestore_host=None, auth_host=None,
        local_gemini_enabled=False, live_ai=True, credits_verified=True,
        credit_verified_until=datetime.now(timezone.utc) + timedelta(minutes=5),
        verified_cloud_model_id=repo.settings.model_id, verified_cloud_location="global", deployed_code_fingerprint="a" * 64)
    for changes in [{"verified_cloud_model_id": ""}, {"model_id": "unverified-model"}, {"verified_cloud_location": ""},
        {"verified_cloud_location": "https://untrusted.invalid"}, {"credits_verified": False}, {"live_ai": False}]:
        repo.settings = replace(settings, **changes)
        assert generate_json(repo, step, "Test", SmokeReply, input_limit=512, output_limit=128).outcome == "NOT_SENT"
    assert calls == [] and not repo.reservations and not repo.writes
    repo.settings = settings
    assert generate_json(repo, step, "Test", SmokeReply, input_limit=512, output_limit=128).error_code == "WORKER_LEASE_REQUIRED"
    assert not calls
    instant = datetime.now(timezone.utc)
    lease = WorkerLease(run_id=step.run_id, generation=1, owner="unit-cloud-owner", expires_at=instant + timedelta(seconds=300),
        execution_deadline_at=instant + timedelta(seconds=240))
    repo.check_worker_lease = lambda value, reserve_seconds: None
    repo.get = lambda _collection, _ident: {"body": {"code_fingerprint": "b" * 64}}
    leased = step.model_copy(update={"worker_lease": lease, "model_id": settings.model_id})
    assert generate_json(repo, leased, "Test", SmokeReply, input_limit=512, output_limit=128).error_code == "CONFIG_SOURCE_MISMATCH"
    assert not calls and not repo.reservations and not repo.writes
    repo.get = lambda _collection, _ident: {"body": {"code_fingerprint": settings.deployed_code_fingerprint}}
    result = generate_json(repo, step.model_copy(update={"worker_lease": lease, "model_id": settings.model_id}),
        "Test", SmokeReply, input_limit=512, output_limit=128)
    assert result.error_code == "OUTPUT_INVALID" and repo.writes[0]["output"] is None
    assert len(repo.reservations) == 1 and [kind for kind, _ in calls] == ["count", "generate"]


def test_sdk_client_selects_explicit_cloud_or_developer_transport_without_fallback(monkeypatch):
    from backend.gateway import _provider_client
    from backend.repository import Conflict
    repo, _step, _calls = setup(monkeypatch)
    constructors = []
    monkeypatch.setattr("google.genai.Client", lambda **kwargs: constructors.append(kwargs))
    _provider_client(repo.settings)
    local = constructors[-1]
    assert local["enterprise"] is False and local["api_key"] == "test-only-not-a-credential"
    assert local["http_options"].api_version == "v1beta" and local["http_options"].retry_options.attempts == 1
    cloud = replace(repo.settings, mode="cloud", local_gemini_enabled=False, live_ai=True, credits_verified=True,
        project_id="unit-project", credit_verified_until=datetime.now(timezone.utc) + timedelta(minutes=5),
        verified_cloud_model_id=repo.settings.model_id, verified_cloud_location="global")
    _provider_client(cloud)
    selected = constructors[-1]
    assert selected["enterprise"] is True and selected["project"] == "unit-project" and selected["location"] == "global"
    assert "api_key" not in selected and selected["http_options"].api_version == "v1"
    assert selected["http_options"].timeout == 30000 and selected["http_options"].retry_options.attempts == 1
    with pytest.raises(Conflict, match="AI_NOT_CONNECTED"): _provider_client(replace(cloud, verified_cloud_model_id=""))
    assert len(constructors) == 2
