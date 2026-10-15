# AML Insight — Genesis

This is the project root. All application code, dependencies, configuration, tools, environments and build output belong here. The parent `context` directory contains local design references; do not publish its internal source materials.

## Run the local application

After the tooling and dependencies below are installed, use three terminals in **Genesis**:

```powershell
# Terminal 1: keep running
npm run emulators

# Terminal 2: create synthetic data, then keep the API running
npm run seed
npm run build
npm run api

# Terminal 3: optional frontend hot reload
npm run dev
```

Open **http://127.0.0.1:8080** for the built application, or **http://127.0.0.1:5173** for frontend development. The API must be running for either view. Firebase emulator UI: http://127.0.0.1:4000.

The local operator fixture is `operator@aml-insight.test` / `local-demo-only`. It is created only in the Auth emulator and is not a cloud credential. Public browsing requires no sign-in. Operator tokens stay in browser memory; sign in again after expiry/reload. Stop servers with Ctrl+C. Emulator records are ephemeral; rerun seed after restarting the emulators.

This version supports source evidence, risk arithmetic, and deterministic discovery diagnostics. **Gemini outputs, durable triage jobs and A5 Evolution analysis are not connected yet.** The live-triage control returns an explicit unavailable response and sends no model request. [Implementation status and remaining gates](docs/implementation-status.md) records the distinction.

```powershell
npm test
# With other emulators stopped; starts and stops isolated local services:
npm run test:integration
# With seeded emulators + API already running, and local Chromium installed:
npm run browser:setup
npm run test:browser
```

## Development tools

- Node.js: use the installed supported runtime (initially 22.7.0).
- Firebase CLI: pinned project-local dependency, **15.34.0**. The older global Firebase CLI is left unchanged.
- Google Cloud CLI: portable **589.0.0**, under `.tools/google-cloud-sdk`.
- Firestore emulator Java runtime: free Eclipse Temurin **21**, under `.tools/java`; downloaded version/hash recorded in `.tools/java-download.json`.
- Python **3.12.15**: managed CPython under `.tools/python`, with the backend environment at `.venv`. Free portable uv **0.13.1** installs it without changing system PATH or the registry. `.python-version` pins the patch version.

From this folder:

```powershell
npm ci --cache .cache/npm
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install-local-tools.ps1
npm run python:setup
npm run python:sync
npm run doctor
npm run firebase -- --version
npm run mcp:check
npm run emulators:check
```

The portable tools installer verifies archive SHA256 checksums. Tools, download archives, emulator binaries and npm cache are ignored local artifacts. It does not modify the global PATH, authenticate, choose a real project, create services or change billing.

## Local Firebase

```powershell
npm run emulators
```

This uses **demo-aml-insight**, not a real Google Cloud project. Auth listens on 127.0.0.1:9099; Firestore on 127.0.0.1:8081; emulator UI on 127.0.0.1:4000. Stop with Ctrl+C.

`npm run emulators:check` starts the emulators, verifies local responses and denial of direct Firestore client reads, and shuts them down automatically. These checks create no cloud resources. The Firebase wrapper selects the project-local Java runtime and emulator binary cache.

The backend selects FIRESTORE_EMULATOR_HOST=127.0.0.1:8081 and FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 by default in local mode and rejects non-loopback overrides. Server-side Firebase token verification and the operator allowlist protect private routes; denying direct client access is not sufficient server-side authorization.

## Codex MCP connection

Open **Genesis itself** as the trusted VS Code/Codex workspace and restart Codex. `.codex/config.toml` starts the pinned Firebase MCP through the project wrapper, restricted to Auth/Firestore feature groups. Core Firebase tools remain available; approval prompts remain enabled. This is a local MCP setup, not an installation of the Firebase marketplace plugin.

The config currently contains this machine's absolute project path; adjust it after moving the checkout. A parent GoogleHack workspace may not load a nested Genesis configuration. Do not enable both this server and the official Firebase plugin for the same project.

`npm run mcp:check` tests initialization and tool discovery only. It does not invoke tools, authenticate a user or verify a cloud connection. A successful smoke check does not mean this running chat has loaded the new server.

## Cloud access: gated until credits are verified

After local setup, interactive account sign-in and verification of a real credited project are still needed. Do not run initialization that creates/selects projects by guesswork.

When explicitly ready to sign in:

```powershell
npm run firebase -- login
npm run gcloud -- auth login
npm run gcloud -- auth application-default login
```

Firebase login uses the CLI's user credential store; never commit credentials. The gcloud wrapper keeps its local configuration under `.tools/gcloud-config`. Do not print credential files or access tokens.

Free tooling and confirmed credits only. No paid subscriptions, billing upgrades, live Gemini calls or cloud resources are approved by running these local checks. Verify the credit balance, expiration and eligible services first; budget alerts are not guaranteed spending caps.

## Design references

- [Architecture and Firestore design](../context/ai-builder-cup-architecture.html)
- [24-task implementation plan](../context/ai-builder-cup-implementation-plan.md)
- [Firestore contract](../context/ai-builder-cup-firestore-contract.json)

The implemented Firestore index declarations mirror the design contract; emulator success does not prove production composite indexes are deployed. The app currently uses standard Firestore documents and immutable public snapshots; execution/usage collections will be wired with the AI worker.

The future target is `genesis-aicb` (project number `638299117256`). Credit balance and expiration are unknown. This does not change the safe local demo-project defaults.

## Setup verification — 15 October 2026

- Verified Node.js 22.7.0, Firebase CLI 15.34.0, Google Cloud SDK 589.0.0, Temurin Java 21.0.12.1 and CPython 3.12.15.
- Firebase MCP initialize/tools-list smoke check passed. No cloud tools invoked.
- Auth/Firestore local emulator check passed; direct Firestore client reads denied; emulators shut down.
- No real Firebase project selected, cloud resources created, billing upgraded or live model calls made.
- Codex must load the Genesis workspace configuration before its MCP tools are available in a new session.
- Account sign-in and credit verification remain prerequisites for live Google Cloud work.
