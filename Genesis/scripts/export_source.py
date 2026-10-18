"""Build a local source-only draft archive; never publish or include private caches."""
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import unquote, urlsplit
import zipfile

from scripts.capture_evaluation import ROOT, code_fingerprint


ROOT_FILES = frozenset({"README.md", "DESIGN.md", "UX-CONTRACT.md", "premium-ui.json", ".gitignore", ".dockerignore",
    ".env.example", ".python-version", "Dockerfile", "package.json", "package-lock.json", "pyproject.toml", "uv.lock",
    "tsconfig.json", "vite.config.ts", "firebase.json", "firestore.rules", "firestore.indexes.json"})
SUFFIXES = {"backend": {".py"}, "frontend": {".ts", ".tsx", ".css", ".html"}, "tests": {".py"},
    "scripts": {".py", ".ps1", ".cjs"}}
DOCUMENTS = frozenset({"bulk-learning-batches.md", "evolution-rule-intelligence.md", "credit-verification.md", "deployment-recovery.md", "cloud-vault-setup.md",
    "evaluation-evidence.md", "evaluation-record.json", "implementation-status.md", "submission-draft.html", "demo-script.md", "local-integration-handoff.md"})
PUBLIC_FILES = frozenset({"docs/workstreams/infrastructure.html", "docs/workstreams/code-completion.html",
    "submission/README.md", "submission/pitch-deck/README.md", "submission/pitch-deck/submission-draft.html",
    "submission/demo-video/README.md", "submission/demo-video/demo-script.md",
    "submission/deployed-prototype/README.md", "submission/deployed-prototype/resource-setup-guide.html",
    "submission/github-repository/README.md", "submission/description/README.md", "submission/description/brief-description.md"})
CONFIGS = frozenset({"deployment.example.json", "cloud-connections.example.json", "rate-card.example.json", "source-publication-approval.example.json", "agent_profiles.json"})
CREDENTIALS = re.compile(rb"AIza[0-9A-Za-z_-]{35}|ya29\.[0-9A-Za-z_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")


def source_files(root, names):
    root = root.resolve()
    result = {}
    for name in sorted(set(names)):
        relative = PurePosixPath(name)
        if (relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name):
            raise ValueError("Invalid source path")
        parts = relative.parts
        allowed = (name in ROOT_FILES or name in PUBLIC_FILES or len(parts) == 2 and (
            relative.suffix in SUFFIXES.get(parts[0], set())
            or parts[0] == "docs" and parts[1] in DOCUMENTS
            or parts[0] == "config" and parts[1] in CONFIGS))
        if not allowed: continue
        path = root / name
        if path.is_symlink() or path.resolve() != path.absolute() or not path.is_file():
            raise ValueError("Source must be an ordinary file within Genesis")
        data = path.read_bytes()
        if CREDENTIALS.search(data): raise ValueError("Credential pattern found in allowed source: " + name)
        result[name] = data
    return result


class _DocumentLinks(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links, self.ids = [], set()
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"): self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if attrs.get(key): self.links.append(attrs[key])


def validate_document_links(files):
    """Resolve documentation links against the archive, never the local filesystem."""
    documents = {}
    for name, data in files.items():
        if not name.endswith((".md", ".html")) or name.startswith("frontend/"): continue
        source = data.decode("utf-8")
        if name.endswith(".md"):
            source = re.sub(r"```[\s\S]*?```|`[^`\n]*`", "", source)
        document = _DocumentLinks(source)
        if name.endswith(".md"):
            document.links.extend(a or b for a, b in re.findall(
                r'!?\[[^\]\n]*\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+"[^"]*")?\s*\)', source))
        documents[name] = document
    for name, document in documents.items():
        for link in document.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc: continue
            path = unquote(parsed.path)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), path)) if path else name
            if path.startswith("/") or "\\" in path or target not in files:
                raise ValueError("Archive document link missing: " + name + " -> " + link)
            if parsed.fragment and target.endswith(".html") and unquote(parsed.fragment) not in (
                    documents.get(target) or _DocumentLinks(files[target].decode("utf-8"))).ids:
                raise ValueError("Archive document anchor missing: " + name + " -> " + link)


def archive_bytes(files, record):
    validate_document_links(files)
    manifest = {"schema_version": 1, "status": "PREPARATION_ONLY", "publication_authorized": False,
        "release_ready": False, "source": record["source"], "checks": record["checks"],
        "source_manifest_hash": record["local_provenance"]["manifest_hash"],
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
        "limitations": ["This archive is an unsubmitted source draft, not a deployed or released revision.",
            "Live investigation, human review, A5, held-out and deployment evidence remain gated.",
            "No credentials, private local evidence or internal context documents belong in this artifact."]}
    payloads = {**files, "release-manifest.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo("Genesis/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return buffer.getvalue()


def main():
    record = json.loads((ROOT / "docs/evaluation-record.json").read_text(encoding="utf-8"))
    fingerprint = code_fingerprint()
    if record["status"] != "LOCAL_VERIFICATION_ONLY" or record["source"]["code_fingerprint"] != fingerprint:
        raise ValueError("Refresh verified evaluation evidence before exporting")
    for kind in ["unit", "emulator_integration"]:
        check = record["checks"][kind]
        if check["failed"] or not check["passed"] or kind == "emulator_integration" and check["skipped"]:
            raise ValueError("Source export requires passing local verification")
    names = subprocess.check_output(["git", "ls-files", "-c", "-o", "--exclude-standard", "-z", "--", "."], cwd=ROOT).decode().split("\0")
    files = source_files(ROOT, [name for name in names if name])
    if not ROOT_FILES | {"backend/api.py", "backend/worker.py"} <= files.keys():
        raise ValueError("Required application sources are missing")
    data = archive_bytes(files, record)
    if code_fingerprint() != fingerprint or any((ROOT / name).read_bytes() != content for name, content in files.items()):
        raise ValueError("Source changed during export")
    digest = hashlib.sha256(data).hexdigest()
    folder = ROOT / ".cache/release"
    if not folder.resolve().is_relative_to(ROOT.resolve()) or folder.resolve() != folder.absolute():
        raise ValueError("Export path must stay in the ordinary Genesis cache directory")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("genesis-source-" + digest[:16] + ".zip")
    if target.is_symlink() or target.resolve() != target.absolute(): raise ValueError("Archive path must not be a link")
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest: raise ValueError("Existing archive checksum mismatch")
    else:
        with target.open("xb") as output: output.write(data)
    print(json.dumps({"archive": str(target.relative_to(ROOT)), "sha256": digest, "source_files": len(files),
        "status": "PREPARATION_ONLY", "published": False}))


if __name__ == "__main__": main()
