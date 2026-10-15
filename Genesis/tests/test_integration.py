"""Real Auth/Firestore emulator checks; never connect to a real project."""
import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(os.getenv("FIRESTORE_EMULATOR_HOST") != "127.0.0.1:8081"
    or os.getenv("FIREBASE_AUTH_EMULATOR_HOST") != "127.0.0.1:9099", reason="Run npm run test:integration")


def test_seed_publication_auth_and_persistence():
    from fastapi.testclient import TestClient
    from backend.api import app
    from backend.config import Settings
    from backend.dataset import DATASET_ID
    from backend.repository import Repository
    from backend.seed import seed

    seed()
    repo = Repository(Settings.load())
    manifest = repo.get("datasets", DATASET_ID)
    seed()  # Source manifest and public snapshot remain stable across repeated seed.
    assert repo.get("datasets", DATASET_ID)["manifest_hash"] == manifest["manifest_hash"]
    assert len(repo.load_dataset().cases) == 112
    with TestClient(app) as client:
        assert client.get("/api/health").json()["live_ai_enabled"] is False
        assert client.get("/api/demo/dashboard").json()["case_count"] == 112
        response = client.get("/api/demo/alerts")
        assert response.headers["cache-control"] == "public, max-age=60"
        cases = response.json()["cases"]
        assert len(cases) == 12
        assert "reference_labels" not in response.text
        assert "reference_reasons" not in response.text
        assert "operator-demo" not in response.text
        assert client.get("/api/demo/alerts/unpublished-case").status_code == 404
        assert client.get("/api/operator/session").status_code == 401
        assert client.post("/api/operator/triage-jobs").status_code == 401
        assert client.get("/api/operator/evaluation", headers={"Authorization": "Bearer invalid"}).status_code == 401

        login = httpx.post("http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=emulator-only",
            json={"email": "operator@aml-insight.test", "password": "local-demo-only", "returnSecureToken": True})
        login.raise_for_status()
        headers = {"Authorization": "Bearer " + login.json()["idToken"]}
        assert client.get("/api/operator/session", headers=headers).json()["uid"] == "operator-demo"
        assert client.post("/api/operator/triage-jobs", headers=headers).status_code == 503
        diagnostic = client.get("/api/operator/evaluation", headers=headers)
        assert diagnostic.status_code == 200
        assert len(diagnostic.json()["discovery_preview"]) == 3
        assert all(row["split"] == "CALIBRATION_DISCOVERY" for row in diagnostic.json()["discovery_preview"])

        alert = next(c["alerts"][0] for c in cases if c["alerts"])
        result = client.post(f'/api/operator/alerts/{alert["id"]}/feedback', headers=headers,
            json={"verdict": "INCONCLUSIVE", "notes": "Missing validated AI output", "expected_revision": 0})
        assert result.status_code == 409  # No fake completed run can accept feedback.
        assert repo.list("feedback_events") == []

        signup = httpx.post("http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signUp?key=emulator-only",
            json={"returnSecureToken": True})
        signup.raise_for_status()
        assert client.get("/api/operator/session", headers={"Authorization": "Bearer " + signup.json()["idToken"]}).status_code == 403

    denial = httpx.get("http://127.0.0.1:8081/v1/projects/demo-aml-insight/databases/(default)/documents/customers")
    assert denial.status_code == 403
