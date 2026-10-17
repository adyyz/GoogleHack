"""Capture local check artifacts; never promote test fixtures to live evidence."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DEFAULTS = {"genuine_investigation_run_id": None, "manual_citation_grounding": None,
    "human_feedback_event_ids": [], "genuine_a5_run_id": None, "frozen_candidate_hash": None,
    "heldout_comparison_id": None, "deployed_revision_ids": [], "signed_out_demo_url": None,
    "public_repository_url": None, "pdf_deck_url": None, "video_url": None, "video_duration_seconds": None,
    "official_eligibility_and_cutoff": None}
PROVENANCE_FIELDS = {"scope", "project_id", "dataset_id", "manifest_hash", "baseline_bundle_id", "publication_id",
    "code_fingerprint", "private_routes_checked", "human_feedback_events", "genuine_model_results_created",
    "candidate_freezes_created", "heldout_comparisons_created"}


def public_provenance(row):
    if row.get("scope") != "LOCAL_EMULATOR_TEST_ONLY" or row.get("project_id") != "demo-aml-insight":
        raise ValueError("Expected demo emulator provenance")
    result = {key: value for key, value in row.items() if key in PROVENANCE_FIELDS}
    for key, value in result.items():
        if key in {"scope", "project_id", "dataset_id"}:
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
                raise ValueError("Invalid public provenance identifier")
        elif key.endswith("_hash") or key in {"code_fingerprint", "baseline_bundle_id", "publication_id"}:
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{24,64}", value):
                raise ValueError("Invalid public provenance hash")
        elif type(value) is not int or not 0 <= value <= 1000000:
            raise ValueError("Invalid public provenance count")
    return result


def _reference(value, pattern):
    if not isinstance(value, str) or not re.fullmatch(pattern, value): raise ValueError("Invalid release reference")
    return value


def _timestamp(value):
    if not isinstance(value, str) or len(value) > 40: raise ValueError("Invalid evidence timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None: raise ValueError("Evidence timestamps require a timezone")
    return value


def _public_url(value):
    if not isinstance(value, str) or len(value) > 2048: raise ValueError("Invalid public evidence URL")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
        or parsed.query or parsed.fragment or parsed.port not in {None, 443}
        or re.search(r"\s|AIza[0-9A-Za-z_-]{35}|ya29\.", value)):
        raise ValueError("Evidence URLs must be public HTTPS links without credentials or query tokens")
    return value


def public_release_evidence(row):
    """Preserve references, not private output or proof of genuine execution.

    Manual grounding uses {investigation_run_id, review_status: PASS|FAIL, reviewed_at}.
    Eligibility uses {eligibility_confirmed, cutoff_at, checked_at, source_url}.
    Unknown keys fail before writing, so invalid prior evidence is never erased.
    """
    if not isinstance(row, dict) or row.keys() - RELEASE_DEFAULTS.keys(): raise ValueError("Unknown release evidence fields")
    result = {key: list(value) if isinstance(value, list) else value for key, value in RELEASE_DEFAULTS.items()}
    for key, value in row.items():
        if value is None: continue
        if key in {"genuine_investigation_run_id", "genuine_a5_run_id", "heldout_comparison_id"}:
            value = _reference(value, r"[0-9a-f]{24,32}")
        elif key == "frozen_candidate_hash": value = _reference(value, r"[0-9a-f]{64}")
        elif key in {"human_feedback_event_ids", "deployed_revision_ids"}:
            pattern = r"[0-9a-f]{24}-[1-9][0-9]{0,8}" if key == "human_feedback_event_ids" else r"[a-z][a-z0-9-]{0,61}[a-z0-9]"
            if not isinstance(value, list) or len(value) > 100 or len(set(map(str, value))) != len(value):
                raise ValueError("Invalid release reference list")
            value = [_reference(item, pattern) for item in value]
        elif key.endswith("_url"): value = _public_url(value)
        elif key == "video_duration_seconds":
            if type(value) is not int or not 0 < value < 180: raise ValueError("Video duration must be under 180 seconds")
        elif key == "manual_citation_grounding":
            if not isinstance(value, dict) or set(value) != {"investigation_run_id", "review_status", "reviewed_at"}:
                raise ValueError("Grounding evidence must contain references only")
            value = {"investigation_run_id": _reference(value["investigation_run_id"], r"[0-9a-f]{24,32}"),
                "review_status": _reference(value["review_status"], r"PASS|FAIL"), "reviewed_at": _timestamp(value["reviewed_at"])}
        elif key == "official_eligibility_and_cutoff":
            if (not isinstance(value, dict) or set(value) != {"eligibility_confirmed", "cutoff_at", "checked_at", "source_url"}
                or type(value["eligibility_confirmed"]) is not bool): raise ValueError("Invalid eligibility evidence references")
            value = {"eligibility_confirmed": value["eligibility_confirmed"], "cutoff_at": _timestamp(value["cutoff_at"]),
                "checked_at": _timestamp(value["checked_at"]), "source_url": _public_url(value["source_url"])}
        result[key] = value
    grounding = result["manual_citation_grounding"]
    if grounding and grounding["investigation_run_id"] != result["genuine_investigation_run_id"]:
        raise ValueError("Grounding does not refer to the preserved investigation")
    return result


def verify_release_references(repo, private, fingerprint):
    """Read persisted links only; never write ledger rows or return private output."""
    from backend.dataset import DATASET_ID, content_hash, generate_dataset, stable_id
    from backend.engine import detect, enrich, prioritize, risk_assessment
    from backend.evolution import candidate_identity
    from backend.models import EvolutionAssessment
    from backend.publisher import MANIFEST, _check_bundle
    from backend.prompts import LEGS
    from backend.validation import validate_model_output
    if (set(private) != {"release_evidence", "expected_code_fingerprint", "expected_manifest_hash",
        "cloud_read_authorized", "manual_grounding_actor_uid"} or private["cloud_read_authorized"] is not True
        or private["expected_code_fingerprint"] != fingerprint or private["expected_manifest_hash"] != MANIFEST):
        raise ValueError("Explicit matching-source private reference verification is required")
    release = public_release_evidence(private["release_evidence"])
    required = ("genuine_investigation_run_id", "manual_citation_grounding", "human_feedback_event_ids",
        "genuine_a5_run_id", "frozen_candidate_hash", "heldout_comparison_id")
    if not all(release[key] for key in required): raise ValueError("Genuine workflow references are incomplete")
    manifest = repo.get("datasets", DATASET_ID)
    if not manifest or manifest.get("state") != "READY" or manifest.get("manifest_hash") != MANIFEST:
        raise ValueError("Frozen release dataset is unavailable or changed")
    run = repo.get("pipeline_runs", release["genuine_investigation_run_id"])
    if (not run or run.get("dataset_id") != DATASET_ID or run.get("kind") != "TRIAGE_ALERT"
        or run.get("state") != "COMPLETE"):
        raise ValueError("A genuine completed investigation is required")
    chain = repo._sealed_chain(None, run)  # The supplied investigation ID is the alert child, not its batch parent.
    _check_bundle(repo, run["config_bundle_id"])
    bundle = repo.get("config_versions", run["config_bundle_id"])
    if bundle["body"].get("provider") != "GOOGLE_CLOUD" or bundle["body"].get("code_fingerprint") != fingerprint:
        raise ValueError("Investigation configuration is not bound to the verified cloud source")
    # Recreate the exact frozen synthetic source offline, never open held-out labels
    # from cloud or trust model-generated evidence. Only this case enters validation.
    data = generate_dataset()
    case = data.cases.get(run.get("case_id"))
    if (data.manifest_hash != MANIFEST or not case
        or not any(alert["id"] == run.get("alert_id") for alert in detect(data, case))):
        raise ValueError("Investigation source case/alert does not match the frozen manifest")
    evidence = enrich(data, case)
    if (chain[0].get("execution_provenance") != "DETERMINISTIC" or chain[0].get("output") != evidence
        or chain[0].get("input_hash") != content_hash(evidence)):
        raise ValueError("Stored deterministic evidence changed")
    for step in chain[1:4]:
        validate_model_output(LEGS[step["leg_id"]][0].model_validate(step["output"]), evidence)
    if (chain[-1].get("execution_provenance") != "DETERMINISTIC"
        or chain[-1].get("output") != prioritize(evidence, risk_assessment(evidence), chain[2]["output"]["suggested_action"])):
        raise ValueError("Stored deterministic prioritization changed")
    actors = set()
    for ident in release["human_feedback_event_ids"]:
        event = repo.get("feedback_events", ident)
        if (not event or event.get("dataset_id") != DATASET_ID or event.get("provenance") != "HUMAN_OPERATOR"
            or event.get("triage_run_id") != run["id"] or event.get("alert_id") != run.get("alert_id")
            or event.get("case_id") != run.get("case_id") or event.get("actor_uid") not in repo.settings.operator_uids):
            raise ValueError("Feedback does not reference an authorized real investigation review")
        actors.add(event["actor_uid"])
    if (private["manual_grounding_actor_uid"] not in actors
        or release["manual_citation_grounding"]["review_status"] != "PASS"):
        raise ValueError("Manual grounding requires the named human reviewer's explicit passing assertion")
    a5 = repo.get("pipeline_runs", release["genuine_a5_run_id"])
    if not a5 or a5.get("dataset_id") != DATASET_ID or a5.get("kind") != "EVOLUTION" or a5.get("state") != "COMPLETE":
        raise ValueError("A genuine completed A5 is required")
    _check_bundle(repo, a5["config_bundle_id"])
    bundle = repo.get("config_versions", a5["config_bundle_id"])
    if bundle["body"].get("provider") != "GOOGLE_CLOUD" or bundle["body"].get("code_fingerprint") != fingerprint:
        raise ValueError("A5 configuration is not bound to the verified cloud source")
    step = repo._leg_step(None, a5, "A5")
    if (step.get("state") != "SUCCEEDED" or step.get("execution_provenance") != "REAL_PROVIDER"
        or step.get("dataset_id") != DATASET_ID or step.get("run_id") != a5["id"]
        or step.get("config_bundle_id") != a5["config_bundle_id"] or not step.get("output")
        or not step.get("validation", {}).get("schema_pass") or not step.get("validation", {}).get("evidence_pass")):
        raise ValueError("Validated real A5 output is required")
    context = repo.evolution_context(a5["analytical_snapshot_id"])  # Rechecks every frozen human/source reference.
    snapshot = context["analytical_inputs"]
    if (snapshot.get("dataset_hash") != MANIFEST or run["config_bundle_id"] not in snapshot.get("config_bundle_ids", [])
        or not set(release["human_feedback_event_ids"]) <= set(snapshot.get("latest_feedback_ids", []))):
        raise ValueError("A5 inputs do not contain the referenced investigation/reviews")
    validate_model_output(EvolutionAssessment.model_validate(step["output"]), context)
    freeze_id = stable_id(DATASET_ID, "heldout")
    freeze = repo.get("candidate_freezes", freeze_id)
    body = {key: value for key, value in (freeze or {}).items()
        if key not in {"id", "dataset_id", "content_hash", "frozen_at", "schema_version", "created_at"}}
    if (not freeze or freeze.get("dataset_id") != DATASET_ID or freeze.get("evolution_run_id") != a5["id"]
        or freeze.get("analytical_snapshot_id") != a5["analytical_snapshot_id"]
        or freeze.get("dataset_hash") != MANIFEST or freeze.get("candidate_hash") != release["frozen_candidate_hash"]
        or freeze.get("frozen_by") not in repo.settings.operator_uids or freeze.get("activation_allowed") is not False
        or content_hash(body) != freeze.get("content_hash")
        or candidate_identity(MANIFEST, freeze["candidate"]) != release["frozen_candidate_hash"]):
        raise ValueError("Explicit frozen candidate provenance is inconsistent")
    comparison = repo.get("simulations", release["heldout_comparison_id"])
    if (release["heldout_comparison_id"] != freeze_id or not comparison or comparison.get("dataset_id") != DATASET_ID
        or comparison.get("state") != "COMPLETE" or comparison.get("freeze_id") != freeze_id
        or comparison.get("freeze_hash") != freeze["content_hash"] or comparison.get("candidate_hash") != freeze["candidate_hash"]
        or not comparison.get("metrics") or not freeze.get("frozen_at") or not comparison.get("started_at")
        or comparison["started_at"] < freeze["frozen_at"]):
        raise ValueError("Stored held-out comparison does not follow the frozen candidate")
    return release


def import_release_references(path, fingerprint):
    """Explicit funded cloud reads only, with every model/task switch disabled."""
    path = Path(path)
    if not path.resolve().is_relative_to((ROOT / ".cache").resolve()) or path.is_symlink() or path.stat().st_size > 65536:
        raise ValueError("Private release references must be a bounded ordinary JSON file under .cache")
    private = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(private, dict): raise ValueError("Invalid private release reference document")
    # Scripts also support direct execution from Genesis without package installation.
    if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
    from backend.config import Settings
    from backend.publisher import PROJECT
    from backend.repository import Repository
    settings = Settings.load()
    if (settings.mode != "cloud" or settings.project_id != PROJECT or settings.firestore_host or settings.auth_host
        or settings.live_ai or settings.local_gemini_enabled or settings.cloud_tasks_enabled
        or not settings.credits_verified or settings.credit_verified_until is None
        or settings.credit_verified_until <= datetime.now(timezone.utc) or not settings.operator_uids
        or "operator-demo" in settings.operator_uids or private.get("cloud_read_authorized") is not True
        or private.get("expected_code_fingerprint") != fingerprint):
        raise ValueError("Verified funded disabled cloud settings and explicit read authorization are required")
    repo = Repository(settings)
    if repo.db.project != PROJECT or repo.db._database != "(default)": raise ValueError("Wrong evidence database")
    return verify_release_references(repo, private, fingerprint)


def code_fingerprint():
    names = subprocess.check_output(["git", "ls-files", "-c", "-o", "--exclude-standard", "--", "."], cwd=ROOT, text=True).splitlines()
    hashes = {}
    roots = {"backend", "frontend", "tests", "scripts", "config"}
    files = {"Dockerfile", ".dockerignore", "pyproject.toml", "uv.lock", "package.json", "package-lock.json", "firebase.json", "firestore.rules", "firestore.indexes.json", ".env.example", "tsconfig.json", "vite.config.ts"}
    for name in sorted(set(names)):
        path = ROOT / name
        if Path(name).parts[0] not in roots and name not in files: continue
        if not path.resolve().is_relative_to(ROOT): raise ValueError("Source path escapes Genesis")
        if path.is_file(): hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def junit_summary(path):
    cases = list(ET.parse(path).getroot().iter("testcase"))
    if not cases: raise ValueError("Missing test cases")
    skipped = sum(case.find("skipped") is not None for case in cases)
    failed = sum(case.find("failure") is not None or case.find("error") is not None for case in cases)
    return {"total": len(cases), "passed": len(cases) - skipped - failed, "skipped": skipped, "failed": failed,
        "artifact_hash": hashlib.sha256(path.read_bytes()).hexdigest()}


def run_unit():
    """Existing pytest command with a matching-source, exact-artifact receipt."""
    folder = ROOT / ".cache"
    folder.mkdir(exist_ok=True)
    receipt_path = folder / "unit-provenance.json"
    fingerprint = code_fingerprint()
    receipt = {"scope": "LOCAL_UNIT_TEST_ONLY", "status": "RUNNING", "code_fingerprint": fingerprint}
    receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    outcome = subprocess.run([sys.executable, "-m", "pytest", "-q", "--junitxml=.cache/unit-results.xml"], cwd=ROOT)
    if outcome.returncode: return outcome.returncode
    if code_fingerprint() != fingerprint: raise ValueError("Source changed during unit verification")
    summary = junit_summary(folder / "unit-results.xml")
    if summary["failed"] or not summary["passed"]: raise ValueError("Unit verification is incomplete")
    receipt.update(status="PASSED", artifact_hash=summary["artifact_hash"], recorded_at=datetime.now(timezone.utc).isoformat())
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def capture(release_input=None):
    def read(name): return json.loads((ROOT / ".cache" / name).read_text(encoding="utf-8-sig"))
    provenance = public_provenance(read("integration-provenance.json"))
    fingerprint = code_fingerprint()
    if provenance["code_fingerprint"] != fingerprint: raise ValueError("Source changed since integration verification")
    unit = junit_summary(ROOT / ".cache/unit-results.xml")
    integration = junit_summary(ROOT / ".cache/integration-results.xml")
    receipt = read("unit-provenance.json")
    if (receipt.get("scope") != "LOCAL_UNIT_TEST_ONLY" or receipt.get("status") != "PASSED"
        or receipt.get("code_fingerprint") != fingerprint or receipt.get("artifact_hash") != unit["artifact_hash"]):
        raise ValueError("Run capture_evaluation.py --run-unit for a matching-source unit receipt")
    if unit["failed"] or integration["failed"] or integration["skipped"] or not unit["passed"] or not integration["passed"]:
        raise ValueError("Local verification is incomplete")
    python = read("python-audit.json")
    npm = read("npm-audit.json")
    production = read("npm-production-audit.json")
    python_findings = [{"name": row["name"], "version": row["version"], "vulnerabilities": row["vulns"]}
        for row in python["dependencies"] if row.get("vulns")]
    smoke_path = ROOT / ".cache/gemini-smoke-result.json"
    smoke = json.loads(smoke_path.read_text(encoding="utf-8-sig")) if smoke_path.exists() else {}
    smoke_fields = ("purpose", "run_id", "step_id", "model", "state", "schema_pass", "provider_reported_tokens",
        "prompt_tokens", "candidate_tokens", "generation_attempts", "live_enabled_after_check", "cost_status", "completed_at")
    target = ROOT / "docs/evaluation-record.json"
    previous = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    release = public_release_evidence(previous.get("release_evidence", {}))
    if release_input is not None: release = import_release_references(release_input, fingerprint)
    has_references = any(value is not None and value != [] for value in release.values())
    binding = None
    if has_references:
        old_binding = ({"code_fingerprint": fingerprint, "release_revision": None} if release_input is not None
            else previous.get("release_evidence_source") or previous.get("source", {}))
        binding = {"code_fingerprint": _reference(old_binding.get("code_fingerprint"), r"[0-9a-f]{64}"),
            "release_revision": old_binding.get("release_revision")}
        if binding["release_revision"] is not None: _reference(binding["release_revision"], r"[0-9a-f]{40}")
    record = {"schema_version": 1, "status": "LOCAL_VERIFICATION_ONLY", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source": {"base_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "uncommitted_worktree": bool(subprocess.check_output(["git", "status", "--porcelain", "--", "."], cwd=ROOT, text=True).strip()),
            "code_fingerprint": fingerprint, "release_revision": None},
        "local_provenance": provenance, "checks": {"unit": unit, "emulator_integration": integration},
        "dependencies": {"python_packages_checked": len(python["dependencies"]), "python_findings": python_findings,
            "python_skipped": [row for row in python["dependencies"] if row.get("skip_reason")],
            "npm_production": production["metadata"]["vulnerabilities"], "npm_development_inclusive": npm["metadata"]["vulnerabilities"],
            "development_findings": [{"package": name, "severity": row["severity"]} for name, row in npm["vulnerabilities"].items()],
            "scope": "Installed Windows Python environment and npm lock; deployed image audit is pending"},
        "connectivity_only": {key: smoke[key] for key in smoke_fields if key in smoke},
        "release_evidence": release,
        "release_evidence_status": ("REPOSITORY_REFERENCES_VERIFIED_ARTIFACTS_UNVERIFIED" if release_input is not None
            else "PRESERVED_REFERENCES_UNVERIFIED" if has_references else "NOT_RECORDED"),
        "release_evidence_source": binding,
        "limitations": ["Local fault/authorization fixtures are not live model or human evidence.",
            "Connectivity smoke is not an AML investigation. Cost remains unknown.",
            "No held-out comparison or optimization performance claim is established.",
            "Funding coverage, cloud identities and publication/submission destinations remain unverified.",
            "Normal local capture does not reverify preserved release references; explicit import only reads referenced persisted records.",
            "Manual grounding remains a named human assertion; artifact access, deployment identity and eligibility require separate verification.",
            "This record does not authorize deployment, billing activation or live requests."], "release_ready": False}
    if code_fingerprint() != fingerprint: raise ValueError("Source changed during evidence capture")
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(json.dumps({"record": "docs/evaluation-record.json", "status": record["status"], "release_ready": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-unit", action="store_true", help="Run existing unit pytest and bind its JUnit to this source")
    parser.add_argument("--release-evidence", type=Path, help="Private reference-only JSON under .cache; never model output/notes")
    parser.add_argument("--verify-release-references", action="store_true", help="Explicitly authorize gated read-only repository verification")
    args = parser.parse_args()
    if bool(args.release_evidence) != args.verify_release_references or args.run_unit and args.release_evidence:
        parser.error("Release import requires both --release-evidence and --verify-release-references, separately from --run-unit")
    try:
        if args.run_unit: raise SystemExit(run_unit())
        capture(args.release_evidence)
    except Exception:
        # A cloud/Pydantic exception can contain private output or credentials.
        raise SystemExit("Evaluation capture refused or interrupted; private exception details suppressed. Review source receipts, reference shapes and persisted provenance before retrying.") from None
