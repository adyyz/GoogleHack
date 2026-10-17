from dataclasses import replace
from datetime import datetime, timedelta, timezone

from backend.config import Settings
from backend.gateway import call_model
from backend.usage import attempt_summary, reconcile, summarize


def test_refusal_has_no_provider_payload_and_requires_current_cloud_credits():
    local = Settings.load()
    assert not local.credits_valid()
    assert call_model(local).outcome == "NOT_SENT"
    assert call_model(local).output is None
    cloud = replace(local, mode="cloud", live_ai=True, credits_verified=True,
        credit_verified_until=datetime.now(timezone.utc) + timedelta(minutes=5))
    assert cloud.credits_valid()
    assert not replace(cloud, credit_verified_until=datetime.now(timezone.utc) - timedelta(seconds=1)).credits_valid()


def test_usage_reconciliation_and_unknown_coverage():
    step = {"usage_status": "PROVIDER_REPORTED", "cost_status": "ESTIMATED", "prompt_tokens": 100,
        "cached_prompt_tokens": 20, "candidate_tokens": 30, "thought_tokens": 10,
        "tool_prompt_tokens": 5, "total_tokens": 145, "estimated_usd_micros": 7,
        "provider_usage_raw": {"secret": True}, "output": {"secret": True}}
    assert sum(reconcile(step).values()) == 145
    assert reconcile({**step, "cached_prompt_tokens": 101}) is None
    assert reconcile({**step, "total_tokens": 140}) is None
    assert reconcile({**step, "thought_tokens": None}) is None
    result = summarize([step, {**step, "attempt_number": 2}, {"usage_status": "UNKNOWN", "cost_status": "UNKNOWN"},
        {"usage_status": "NOT_APPLICABLE", "cost_status": "NOT_APPLICABLE"}])
    assert result["total_tokens"] == 290
    assert result["known_estimated_usd_micros"] == 14
    assert result["unknown_attempts"] == 1
    assert result["not_applicable_attempts"] == 1
    assert summarize([])["total_tokens"] is None
    assert summarize([step, {**step, "thought_tokens": None}])["categories"] is None
    assert "output" not in attempt_summary(step)
    assert "provider_usage_raw" not in attempt_summary(step)


def test_interim_gemini_requires_separate_local_free_tier_gates(monkeypatch):
    local = Settings.load()
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    configured = replace(local, local_gemini_enabled=True, local_gemini_free_verified=True,
        local_gemini_verified_until=expiry)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert not configured.ai_authorized()
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-credential")
    assert configured.ai_authorized()
    assert not configured.credits_valid()  # Developer free tier never verifies cloud credits.
    assert configured.active_model_id == "gemini-3.5-flash-lite"
    assert configured.ai_verified_until == expiry
    assert not replace(configured, mode="cloud").local_gemini_valid()
    assert not replace(configured, project_id="real-project").local_gemini_valid()
    assert not replace(configured, local_gemini_free_verified=False).local_gemini_valid()
    assert not replace(configured, local_gemini_verified_until=datetime.now(timezone.utc) - timedelta(seconds=1)).local_gemini_valid()
    assert not replace(configured, local_gemini_model="unverified-model").local_gemini_valid()
