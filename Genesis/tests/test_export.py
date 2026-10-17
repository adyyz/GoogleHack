"""Source archive boundaries; credentials below are synthetic in-memory fixtures."""
import hashlib
import io
import json
import zipfile

import pytest

from scripts.export_source import archive_bytes, source_files, validate_document_links


def test_export_allowlist_excludes_private_material_and_pins_exact_sources(tmp_path):
    names = {"README.md": b"Draft", "backend/api.py": b"pass\n", "frontend/index.html": b"<main>Demo</main>",
        ".env.example": b"LIVE_AI_ENABLED=false\n", "config/deployment.example.json": b"{}",
        "context/internal.md": b"private plan", ".env": b"private environment", ".codex/config.toml": b"private path",
        ".cache/emulator-data.json": b"private evidence", "backend/credentials.json": b"private credentials",
        "docs/analyst-notes.md": b"private notes", "AGENTS.md": b"internal references"}
    for name, data in names.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    files = source_files(tmp_path, list(names))
    assert set(files) == {"README.md", "backend/api.py", "frontend/index.html", ".env.example", "config/deployment.example.json"}
    record = {"source": {"base_revision": "unit-revision", "uncommitted_worktree": True, "code_fingerprint": "unit-hash"},
        "checks": {}, "local_provenance": {"manifest_hash": "unit-source-manifest"}}
    data = archive_bytes(files, record)
    assert data == archive_bytes(dict(reversed(list(files.items()))), record)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert set(archive.namelist()) == {"Genesis/" + name for name in [*files, "release-manifest.json"]}
        manifest = json.loads(archive.read("Genesis/release-manifest.json"))
        assert manifest["status"] == "PREPARATION_ONLY" and not manifest["publication_authorized"] and not manifest["release_ready"]
        assert manifest["files"] == {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        assert all(archive.read("Genesis/" + name) == content for name, content in files.items())
    for name in ["../README.md", "C:/README.md", "backend\\api.py"]:
        with pytest.raises(ValueError, match="Invalid source path"): source_files(tmp_path, [name])
    for credential in [b"AIza" + b"a" * 35, b"ya29." + b"a" * 25, b"-----BEGIN " + b"PRIVATE KEY-----"]:
        (tmp_path / "backend/api.py").write_bytes(credential)
        with pytest.raises(ValueError, match="Credential pattern"): source_files(tmp_path, ["backend/api.py"])


def test_export_includes_only_reviewed_submission_documents_and_resolves_archive_links(tmp_path):
    names = {"README.md": b"[Submission](submission/README.md) [External](https://example.invalid/missing)\n"
            b"`[Example](not-a-file.md)`\n```markdown\n[Example](also-not-a-file.md)\n```\n",
        "submission/README.md": b"[Guide](deployed-prototype/resource-setup-guide.html#start)",
        "submission/deployed-prototype/resource-setup-guide.html": b'<h1 id="start">Guide</h1><a href="../../README.md">Home</a>',
        "docs/workstreams/infrastructure.html": b'<a href="code-completion.html">Code</a>',
        "docs/workstreams/code-completion.html": b'<a href="infrastructure.html">Infrastructure</a>',
        "config/rate-card.example.json": b'{"verified": false}',
        "submission/pitch-deck/draft.pdf": b"excluded binary",
        "submission/github-repository/previous-source.zip": b"excluded archive",
        "submission/private-notes.md": b"excluded unreviewed text",
        "docs/workstreams/credentials.html": b"excluded unreviewed page",
        "context/internal.md": b"private context"}
    for name, data in names.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    files = source_files(tmp_path, names)
    assert set(files) == {"README.md", "submission/README.md", "submission/deployed-prototype/resource-setup-guide.html",
        "docs/workstreams/infrastructure.html", "docs/workstreams/code-completion.html", "config/rate-card.example.json"}
    assert validate_document_links(files) is None
    record = {"source": {}, "checks": {}, "local_provenance": {"manifest_hash": "frozen"}}
    first = archive_bytes(files, record)
    assert first == archive_bytes(dict(reversed(list(files.items()))), record)
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {"Genesis/" + name for name in [*files, "release-manifest.json"]}
    # Credentials are refused even on newly allowlisted submission pages.
    (tmp_path / "docs/workstreams/infrastructure.html").write_bytes(b"AIza" + b"a" * 35)
    with pytest.raises(ValueError, match="Credential pattern"):
        source_files(tmp_path, names)


@pytest.mark.parametrize("link", ["context/internal.md", ".cache/run.json", "/README.md",
    "%2e%2e/context/internal.md", "submission\\secret.md", "submission/missing.md",
    "docs/submission-draft.html#missing"])
def test_export_refuses_document_links_outside_exact_archive_or_missing_anchors(link):
    files = {"README.md": ("[Evidence](" + link + ")").encode(),
        "docs/submission-draft.html": b'<h1 id="present">Draft</h1>'}
    with pytest.raises(ValueError, match="Archive document (link|anchor) missing"):
        archive_bytes(files, {"source": {}, "checks": {}, "local_provenance": {"manifest_hash": "frozen"}})
