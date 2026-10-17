"""Unit tests for capability-driven model profiles and Secret Manager loading."""
import json
import pytest
from backend.agent_profiles import AgentCapability, AgentProfilesRegistry, ModelProfile, load_agent_profiles
from backend.config import Settings
from backend.prompts import LEG_CAPABILITIES


def test_checked_in_profile_example_loads_and_keeps_one_primary_model():
    from pathlib import Path
    from scripts.export_source import source_files
    root = Path(__file__).resolve().parents[1]
    name = "config/agent_profiles.json"
    exported = source_files(root, [name])
    assert name in exported
    registry = AgentProfilesRegistry(exported[name].decode())
    profiles = registry.frozen_profiles
    assert set(profiles) == {"A2", "A3", "A4", "A5"}
    assert {profile["model_id"] for profile in profiles.values()} == {"gemini-3.5-flash"}
    assert all(profile["thinking_level"] == "MINIMAL" for profile in profiles.values())


SAMPLE_SECRET_JSON = json.dumps({
    "version": "1.0",
    "profiles": {
        "fast_triage": {
            "capability": "FAST_CLASSIFICATION",
            "model_id": "gemini-2.5-flash-lite",
            "description": "Fast triage",
            "thinking_level": "MINIMAL",
            "temperature": 0.1
        },
        "risk_explainer": {
            "capability": "STRUCTURED_REASONING",
            "model_id": "gemini-2.5-flash",
            "description": "Risk explainer",
            "thinking_level": "MINIMAL",
            "temperature": 0.2
        },
        "deep_investigation": {
            "capability": "DEEP_INVESTIGATION",
            "model_id": "gemini-2.5-pro",
            "description": "Deep investigation",
            "thinking_level": "MEDIUM",
            "temperature": 0.2
        },
        "meta_evolution": {
            "capability": "META_EVOLUTION",
            "model_id": "gemini-2.5-pro",
            "description": "Meta evolution",
            "thinking_level": "MEDIUM",
            "temperature": 0.1
        }
    },
    "leg_mapping": {
        "A3": "fast_triage",
        "A2": "risk_explainer",
        "A4": "deep_investigation",
        "A5": "meta_evolution"
    }
})


def test_registry_fallback_when_empty():
    registry = AgentProfilesRegistry(raw_json=None, fallback_model="gemini-3.5-flash")
    assert not registry.is_custom
    # Without custom JSON, all legs fall back safely to fallback_model
    assert registry.get_for_leg("A3").model_id == "gemini-3.5-flash"
    assert registry.get_for_leg("A4").model_id == "gemini-3.5-flash"
    assert all(registry.get_for_leg(leg).thinking_level == "MINIMAL" for leg in LEG_CAPABILITIES)


def test_registry_with_secret_json():
    registry = AgentProfilesRegistry(raw_json=SAMPLE_SECRET_JSON, fallback_model="gemini-3.5-flash")
    assert registry.is_custom
    # With custom JSON, distinct models and capabilities are returned
    a3_profile = registry.get_for_leg("A3")
    assert a3_profile.model_id == "gemini-2.5-flash-lite"
    assert a3_profile.capability == AgentCapability.FAST_CLASSIFICATION
    assert a3_profile.temperature == 0.1

    a4_profile = registry.get_for_leg("A4")
    assert a4_profile.model_id == "gemini-2.5-pro"
    assert a4_profile.capability == AgentCapability.DEEP_INVESTIGATION
    assert a4_profile.thinking_level == "MEDIUM"

    a2_profile = registry.get_for_leg("A2")
    assert a2_profile.model_id == "gemini-2.5-flash"

    a5_profile = registry.get_for_leg("A5")
    assert a5_profile.model_id == "gemini-2.5-pro"


def test_get_by_capability():
    registry = AgentProfilesRegistry(raw_json=SAMPLE_SECRET_JSON)
    fast = registry.get_for_capability(AgentCapability.FAST_CLASSIFICATION)
    assert fast.model_id == "gemini-2.5-flash-lite"

    deep = registry.get_for_capability(AgentCapability.DEEP_INVESTIGATION)
    assert deep.model_id == "gemini-2.5-pro"


def test_prompts_leg_capabilities():
    assert LEG_CAPABILITIES["A3"] == AgentCapability.FAST_CLASSIFICATION
    assert LEG_CAPABILITIES["A2"] == AgentCapability.STRUCTURED_REASONING
    assert LEG_CAPABILITIES["A4"] == AgentCapability.DEEP_INVESTIGATION
    assert LEG_CAPABILITIES["A5"] == AgentCapability.META_EVOLUTION


def test_settings_model_authorization():
    # Local mode with fallback
    settings = Settings.load()
    assert settings.is_model_authorized(settings.active_model_id)

    # Custom profiles configured
    custom_settings = Settings(
        mode="cloud",
        project_id="genesis-aicb",
        firestore_host=None,
        auth_host=None,
        live_ai=True,
        model_id="gemini-2.5-flash",
        operator_uids=frozenset({"op-1"}),
        credits_verified=True,
        credit_verified_until=None,
        verified_cloud_model_id="gemini-2.5-flash",
        verified_cloud_location="australia-southeast1",
        agent_profiles_json=SAMPLE_SECRET_JSON
    )
    # Profiles remain configurable; only the separately verified primary model may execute.
    assert custom_settings.agent_profiles.is_custom
    assert "gemini-2.5-flash-lite" in custom_settings.agent_profiles.authorized_models
    assert "gemini-2.5-pro" in custom_settings.agent_profiles.authorized_models
    assert custom_settings.agent_profiles.get_for_leg("A4").model_id == "gemini-2.5-pro"
    assert not custom_settings.is_model_authorized("gemini-2.5-pro", "A4")


def test_gateway_refuses_unverified_custom_model_before_provider_or_reservation(monkeypatch):
    from dataclasses import replace
    from backend.gateway import generate_json
    from backend.gemini_smoke import SmokeReply
    from test_gateway import setup
    repo, step, calls = setup(monkeypatch)
    repo.settings = replace(repo.settings, agent_profiles_json=SAMPLE_SECRET_JSON)
    profile = repo.settings.agent_profiles.get_for_leg("A4")
    result = generate_json(repo, step.model_copy(update={"model_id": profile.model_id}), "Test instruction", SmokeReply,
        input_limit=512, output_limit=128, model_id=profile.model_id,
        thinking_level=profile.thinking_level, temperature=profile.temperature)
    assert result.outcome == "NOT_SENT" and result.error_code == "MODEL_NOT_VERIFIED"
    assert not calls and not repo.reservations and not repo.writes


def test_invalid_explicit_profile_config_refuses_instead_of_selecting_defaults(monkeypatch):
    for raw in ["{bad-json", "[]", '{"profiles": {}}']:
        with pytest.raises(ValueError, match="Invalid agent profiles configuration"):
            AgentProfilesRegistry(raw)
    for changes in [{"thinking_level": "STANDARD"}, {"temperature": float("nan")},
        {"temperature": -0.1}, {"temperature": True}, {"max_output_tokens": 3000}, {"unexpected": True}]:
        body = json.loads(SAMPLE_SECRET_JSON)
        body["profiles"]["fast_triage"].update(changes)
        with pytest.raises(ValueError, match="Invalid agent profiles configuration"):
            AgentProfilesRegistry(json.dumps(body))
    monkeypatch.setenv("AGENT_PROFILES_JSON", "{bad-json")
    with pytest.raises(ValueError, match="Invalid agent profiles configuration"): Settings.load()
    # An already captured empty Settings value cannot pick up a later environment change.
    assert load_agent_profiles("", fallback_model="gemini-3.5-flash").is_custom is False


def test_custom_registry_does_not_extend_verified_cloud_model_or_location():
    from dataclasses import replace
    from datetime import timedelta
    from backend.repository import now
    settings = replace(Settings.load(), mode="cloud", live_ai=True, credits_verified=True,
        credit_verified_until=now() + timedelta(minutes=5), verified_cloud_model_id="gemini-3.5-flash",
        verified_cloud_location="global", agent_profiles_json=SAMPLE_SECRET_JSON)
    assert settings.cloud_model_valid() and settings.is_model_authorized("gemini-3.5-flash")
    assert not settings.is_model_authorized("gemini-2.5-pro", "A4")
    assert not replace(settings, model_id="unverified-fallback").cloud_model_valid()
    assert not replace(settings, verified_cloud_location="").is_model_authorized(settings.model_id)


def test_complete_generation_profiles_are_immutable_and_workers_ignore_later_settings():
    from copy import deepcopy
    from dataclasses import replace
    from google.api_core.exceptions import AlreadyExists
    from backend.jobs import _leg_profile
    from backend.repository import Repository
    body = json.loads(SAMPLE_SECRET_JSON)
    for value in body["profiles"].values(): value["model_id"] = "gemini-3.5-flash-lite"
    settings = replace(Settings.load(), local_gemini_enabled=True, agent_profiles_json=json.dumps(body))
    records = {}
    repo = object.__new__(Repository)
    repo.settings = settings
    def create(_collection, ident, value):
        if ident in records: raise AlreadyExists("in-memory immutable configuration")
        records[ident] = {"id": ident, **deepcopy(value)}
    repo.create = create
    repo.get = lambda _collection, ident: deepcopy(records.get(ident))
    original_id = repo.ensure_baseline()
    original = deepcopy(records[original_id])
    pinned = original["body"]["generation_profiles"]["A4"]
    assert pinned["model_id"] == settings.active_model_id and pinned["thinking_level"] == "MEDIUM"
    assert pinned["temperature"] == 0.2 and pinned["max_output_tokens"] == 2048
    body["profiles"]["deep_investigation"]["temperature"] = 0.9
    repo.settings = replace(settings, agent_profiles_json=json.dumps(body))
    assert repo.ensure_baseline() != original_id
    assert records[original_id] == original
    assert _leg_profile(repo, original_id, "A4").temperature == 0.2


def test_legacy_bundle_cannot_silently_switch_to_a_new_profile_model(monkeypatch):
    from types import SimpleNamespace
    from backend.agent_profiles import frozen_profile
    from backend.jobs import triage_leg
    from test_gateway import setup
    repo, step, calls = setup(monkeypatch)
    bundle = {"body": {"model_id": repo.settings.active_model_id}}
    legacy = frozen_profile(bundle, "A3", repo.settings.active_model_id)
    assert legacy.model_id == repo.settings.active_model_id and legacy.thinking_level == "MINIMAL"
    assert legacy.temperature is None and legacy.max_output_tokens is None
    repo.get = lambda *_args: bundle
    result = triage_leg(repo, {"config_bundle_id": step.config_bundle_id},
        SimpleNamespace(model_id="gemini-2.5-pro", leg_id="A3"), {}, {}, {})
    assert result.error_code == "CONFIG_MISMATCH" and not calls and not repo.reservations


def test_frozen_parameters_drive_request_and_tampering_refuses_before_provider(monkeypatch):
    from backend.gateway import generate_json
    from backend.gemini_smoke import SmokeReply
    from test_gateway import setup
    repo, step, calls = setup(monkeypatch)
    profile = ModelProfile(model_id=repo.settings.active_model_id, thinking_level="LOW", temperature=0.1, max_output_tokens=768)
    bundle = {"body": {"generation_profiles": {"A3": profile.model_dump(mode="json")}}}
    repo.get = lambda *_args: bundle
    step = step.model_copy(update={"leg_id": "A3"})
    for thinking, temperature in [("HIGH", 0.1), ("LOW", 0.8), ("STANDARD", 0.1)]:
        result = generate_json(repo, step, "Fixture", SmokeReply, input_limit=2048, output_limit=768,
            evidence={}, thinking_level=thinking, temperature=temperature)
        assert result.error_code == "CONFIG_GENERATION_MISMATCH"
        assert not calls and not repo.reservations and not repo.writes
    result = generate_json(repo, step, "Fixture", SmokeReply, input_limit=2048, output_limit=768,
        evidence={}, thinking_level="LOW", temperature=0.1)
    assert result.error_code == "OUTPUT_INVALID" and repo.writes[0]["output"] is None
    request = repo.reservations[0].input_snapshot
    assert request["generation_config"]["thinking_config"] == {"thinking_level": "LOW"}
    assert request["generation_config"]["temperature"] == 0.1 and request["model_id"] == repo.settings.active_model_id

