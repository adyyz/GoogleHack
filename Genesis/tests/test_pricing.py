"""Synthetic rate arithmetic only; no real rate approval or successful model output."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from backend.config import Settings
from backend.dataset import content_hash
from backend.pricing import configured_card, estimate, frozen_card, parse_card


def card_fixture():
    instant = datetime.now(timezone.utc)
    body = {"verified": True, "verified_by": "UNIT_TEST_ONLY", "provider": "GOOGLE_CLOUD",
        "service": "aiplatform.googleapis.com", "currency": "USD", "model_id": "test-only-model", "location": "global",
        "billing_mode": "STANDARD_ON_DEMAND_TEXT", "usage_semantics": "PROMPT_INCLUDES_CACHE_THOUGHTS_SEPARATE_V1",
        "source_url": "https://cloud.google.com/vertex-ai/generative-ai/pricing#unit-fixture-not-real-rates",
        "input_sku": "test-input", "cached_input_sku": "test-cache", "output_sku": "test-output",
        "effective_from": (instant - timedelta(hours=1)).isoformat(), "effective_until": (instant + timedelta(hours=1)).isoformat(),
        "max_input_tokens": 8192, "uncached_prompt_usd_micros_per_million": 1000000,
        "cached_prompt_usd_micros_per_million": 250000, "output_including_thoughts_usd_micros_per_million": 2000000}
    settings = replace(Settings.load(), mode="cloud", model_id=body["model_id"], verified_cloud_location="global",
        verified_rate_card_json=json.dumps(body))
    return body, settings, instant


def usage_fixture():
    return {"usage_status": "PROVIDER_REPORTED", "prompt_tokens": 100, "cached_prompt_tokens": 20,
        "candidate_tokens": 10, "thought_tokens": 5, "tool_prompt_tokens": 0, "total_tokens": 115,
        "provider_service_tier": "standard"}


def test_verified_rate_math_counts_cache_once_and_rounds_once():
    from types import SimpleNamespace
    body, settings, instant = card_fixture()
    card = configured_card(settings)
    step = SimpleNamespace(model_id=settings.model_id)
    assert estimate(card, usage_fixture(), settings, step, instant) == {"cost_status": "ESTIMATED", "estimated_usd_micros": 115}
    tiny = {**usage_fixture(), "prompt_tokens": 1, "cached_prompt_tokens": 1,
        "candidate_tokens": 0, "thought_tokens": 0, "total_tokens": 1}
    assert estimate(card, tiny, settings, step, instant)["estimated_usd_micros"] == 1
    assert estimate(card, usage_fixture(), settings, step, instant + timedelta(hours=2))["cost_status"] == "UNKNOWN"
    for change in [{"thought_tokens": None}, {"cached_prompt_tokens": 101}, {"total_tokens": 100},
        {"provider_service_tier": "priority"}, {"provider_service_tier": None}, {"usage_status": "UNKNOWN"},
        {"tool_prompt_tokens": 1, "total_tokens": 116}]:
        result = estimate(card, {**usage_fixture(), **change}, settings, step, instant)
        assert result == {"cost_status": "UNKNOWN", "estimated_usd_micros": None}
    assert estimate(card, usage_fixture(), replace(settings, verified_cloud_location="other"), step, instant)["cost_status"] == "UNKNOWN"
    assert estimate(card, usage_fixture(), settings, SimpleNamespace(model_id="other"), instant)["cost_status"] == "UNKNOWN"
    assert estimate(card.model_copy(update={"max_input_tokens": 99}), usage_fixture(), settings, step, instant)["cost_status"] == "UNKNOWN"


def test_rate_configuration_refuses_unreviewed_ambiguous_or_wrong_scope():
    body, settings, _instant = card_fixture()
    assert configured_card(replace(settings, verified_rate_card_json="")) is None
    for changes in [{"verified": False}, {"verified": 1}, {"currency": "AUD"}, {"effective_until": body["effective_from"]},
        {"uncached_prompt_usd_micros_per_million": 0.5}, {"source_url": "https://untrusted.invalid/pricing"},
        {"source_url": "https://cloud.google.com/pricing?key=DO_NOT_PRINT"}, {"effective_from": "2026-01-01T00:00:00"}]:
        with pytest.raises(ValueError, match="configuration is invalid"):
            parse_card(json.dumps({**body, **changes}))
    with pytest.raises(ValueError, match="does not match"):
        configured_card(replace(settings, model_id="other"))


def test_deployment_source_fingerprint_requires_exact_sha256(monkeypatch):
    monkeypatch.setenv("DEPLOYED_CODE_FINGERPRINT", "wrong")
    with pytest.raises(ValueError, match="verified SHA256"):
        Settings.load()
    monkeypatch.setenv("DEPLOYED_CODE_FINGERPRINT", "a" * 64)
    assert Settings.load().deployed_code_fingerprint == "a" * 64


def test_multi_alert_and_retry_usage_sums_only_known_estimates():
    from types import SimpleNamespace
    from backend.usage import summarize
    _body, settings, instant = card_fixture()
    usage = usage_fixture()
    priced = {**usage, **estimate(configured_card(settings), usage, settings,
        SimpleNamespace(model_id=settings.model_id), instant)}
    attempts = [{**priced, "run_id": run, "attempt_number": attempt}
        for run, attempt in [("child-a", 1), ("child-a", 2), ("child-b", 1)]]
    attempts += [{"usage_status": "UNKNOWN", "cost_status": "UNKNOWN"},
        {"usage_status": "NOT_APPLICABLE", "cost_status": "NOT_APPLICABLE", "estimated_usd_micros": None}]
    totals = summarize(attempts)
    assert totals["known_estimated_usd_micros"] == 345 and totals["total_tokens"] == 345
    assert totals["unknown_attempts"] == 1 and totals["not_applicable_attempts"] == 1


def test_frozen_rate_lookup_does_not_follow_new_deployment_card():
    from types import SimpleNamespace
    body, settings, _instant = card_fixture()
    version = {"kind": "RATE_CARD", "origin": "BASELINE", "body": body}
    ident = content_hash(version)
    row = {**version, "content_hash": ident}
    records = {"bundle": {"component_ids": {"RATE_CARD": ident}}, ident: row}
    repo = SimpleNamespace(settings=replace(settings, verified_rate_card_json=""), get=lambda _c, key: records.get(key))
    assert frozen_card(repo, SimpleNamespace(config_bundle_id="bundle"))[0] == ident
    row["body"] = {**body, "input_sku": "tampered"}
    assert frozen_card(repo, SimpleNamespace(config_bundle_id="bundle")) == (None, None)


def test_failed_generation_keeps_pricing_provenance_without_model_output(monkeypatch):
    from types import SimpleNamespace
    from backend.gateway import generate_json
    from backend.gemini_smoke import SmokeReply
    from backend.models import WorkerLease
    from google.genai.types import ServiceTier
    from test_gateway import setup
    body, settings, instant = card_fixture()
    repo, step, calls = setup(monkeypatch)
    settings = replace(settings, project_id="unit-project", live_ai=True, credits_verified=True,
        credit_verified_until=instant + timedelta(minutes=5), verified_cloud_model_id=settings.model_id,
        local_gemini_enabled=False, deployed_code_fingerprint="a" * 64)
    repo.settings = settings
    version = {"kind": "RATE_CARD", "origin": "BASELINE", "body": body}
    ident = content_hash(version)
    records = {step.config_bundle_id: {"component_ids": {"RATE_CARD": ident},
        "body": {"code_fingerprint": settings.deployed_code_fingerprint}}, ident: {**version, "content_hash": ident}}
    repo.get = lambda _c, key: records.get(key)
    repo.check_worker_lease = lambda *_args, **_kwargs: None
    lease = WorkerLease(run_id=step.run_id, generation=1, owner="test-only", expires_at=instant + timedelta(seconds=300),
        execution_deadline_at=instant + timedelta(seconds=240))
    step = step.model_copy(update={"model_id": settings.model_id, "worker_lease": lease})
    class FaultClient:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        @property
        def models(self): return self
        def count_tokens(self, **_kwargs): return SimpleNamespace(total_tokens=100)
        def generate_content(self, **kwargs):
            assert kwargs["config"]["service_tier"] == "standard"
            return SimpleNamespace(text="invalid-test-json", response_id="test-only", usage_metadata=SimpleNamespace(
                prompt_token_count=100, cached_content_token_count=20, candidates_token_count=10, thoughts_token_count=5,
                tool_use_prompt_token_count=0, total_token_count=115, service_tier=ServiceTier.STANDARD))
    monkeypatch.setattr("backend.gateway._provider_client", lambda _settings: FaultClient())
    result = generate_json(repo, step, "Fault test", SmokeReply, input_limit=512, output_limit=128)
    assert result.error_code == "OUTPUT_INVALID" and repo.writes[0]["output"] is None
    assert repo.reservations[0].rate_card_id == ident
    assert repo.writes[0]["estimated_usd_micros"] == 115 and repo.writes[0]["cost_status"] == "ESTIMATED"
