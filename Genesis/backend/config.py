import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    mode: str
    project_id: str
    firestore_host: str | None
    auth_host: str | None
    live_ai: bool
    model_id: str
    operator_uids: frozenset[str]

    @classmethod
    def load(cls):
        mode = os.getenv("APP_MODE", "local")
        if mode not in {"local", "cloud"}: raise ValueError("APP_MODE must be local or cloud")
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "demo-aml-insight" if mode == "local" else "")
        firestore = os.getenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8081" if mode == "local" else "") or None
        auth = os.getenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099" if mode == "local" else "") or None
        if mode == "local":
            if project != "demo-aml-insight": raise ValueError("Local mode requires the demo-aml-insight project")
            for host in [firestore, auth]:
                if not host or urlparse("http://" + host).hostname not in {"localhost", "127.0.0.1"}:
                    raise ValueError("Local emulators must use loopback hosts")
            os.environ["FIRESTORE_EMULATOR_HOST"] = firestore
            os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = auth
        elif not project or project.startswith("demo-") or firestore or auth:
            raise ValueError("Cloud mode requires a real project and forbids emulator settings")
        uids = frozenset(filter(None, os.getenv("OPERATOR_UIDS", "operator-demo" if mode == "local" else "").split(",")))
        live_ai = os.getenv("LIVE_AI_ENABLED", "false").lower() == "true"
        if live_ai and (mode != "cloud" or os.getenv("CREDITS_VERIFIED", "false").lower() != "true"):
            raise ValueError("Live AI requires cloud mode and explicit verified credit coverage")
        return cls(mode, project, firestore, auth, live_ai, os.getenv("GEMINI_MODEL", "gemini-3.5-flash"), uids)
