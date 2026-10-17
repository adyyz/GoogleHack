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

Cloud sign-in uses an explicit Google popup through the official Firebase JavaScript SDK with in-memory persistence. Enable the Google provider and authorize the deployed hostname in Firebase Authentication. `FIREBASE_WEB_API_KEY` must be the project's public Firebase web-app configuration; never use the private Gemini key. A returned ID token is accepted only after the server's existing UID allowlist check. The SDK session is cleared after the attempt; tokens stay out of URLs and persistent browser storage. Configuration failures offer explicit retry; closing the dialog prevents late sign-in results from being accepted. Local mode retains the emulator email/password form. Backend service accounts authenticate services, while the Google account identifies the human operator. See [current deployment evidence](docs/deployment-recovery.md) for the difference between configured providers and a verified browser login.

This version supports source evidence, risk arithmetic, deterministic discovery diagnostics and persisted local triage runs. Default local triage seals evidence enrichment, records `AI_NOT_CONNECTED` at A2 and sends no model request. The separate opt-in Developer API worker is implemented; **a genuine AML investigation and A5 analysis have not run.** Further live calls require the agreed bounded test approval and verified free-tier/credit coverage. [Implementation status and remaining gates](docs/implementation-status.md) records the distinction.

The **public Usage panel** is on the investigation workspace and requires no sign-in. It shows only sanitized aggregate usage and reports no model usage before any attempt. The **operator dialog** opens from a single parent-run completion notification or "View run usage" and shows private leg/attempt details. The **Admin** screen lets allowlisted operators inspect aggregate usage, recent runs and audit history. **Admin-only controls** change today's UTC live-AI switch and daily attempt limit; enabling also requires verified cloud credits and an unexpired verification. Local mode cannot enable live AI. Estimates are USD model costs, not cloud invoices or remaining credit balances.

Analyst feedback is for one selected alert and remains disabled until its private alert record links to a completed, validated investigation. Local refused runs do not permit feedback. Use "Refresh status" to reread the latest durable run; the browser does not poll.

The interim Developer API connection has passed one explicitly approved smoke test (74 provider-reported tokens). This does not complete AML triage or verify deployment credits. `scripts/with-gemini-secret.ps1` loads `testing_free_gemini_api` version 2 into process memory; its default `Check` action suppresses the payload and makes no model call. `-Action Smoke` is live: it pre-counts a tiny schema-bearing prompt, allows one generation attempt with a 128-token output cap and no retry, records the real result only in the local emulator ledger, and disables today's switch afterward. Do not run Smoke as part of routine tests. The default gateway remains closed; the separate worker requires explicit opt-in.

```powershell
npm test
# With other emulators stopped; starts and stops isolated local services:
npm run test:integration
# With seeded emulators + API already running, and local Chromium installed:
npm run browser:setup
npm run test:browser
```

If PowerShell blocks `npm.ps1`, use `npm.cmd` for these commands. Funding remains unverified; the [credit verification guide](docs/credit-verification.md) lists the console fields needed before live integration.

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

Run regression browser journeys against an owned, closed-AI test environment, rather than an operator's active preview. The browser runner accepts `GENESIS_BROWSER_BASE_URL` for a separate loopback API; integration tests accept explicit loopback Auth/Firestore ports. This allows fresh test data without overwriting genuine local investigation/review evidence.

The npm override pins `@grpc/grpc-js` to `1.14.6`, already used by the pinned Firebase CLI. This replaces the Firebase umbrella package's old transitive Firestore pin affected by [the upstream certificate-authentication advisory](https://github.com/grpc/grpc-node/security/advisories/GHSA-m9gg-hp2v-232j). App code imports Firebase app/auth only; final Python images receive compiled browser assets, not node_modules. The override can be removed when the pinned Firebase release resolves to a patched version itself. Production npm findings and development-tool/image findings are recorded separately in the evaluation record.

```powershell
npm run emulators
```

This uses **demo-aml-insight**, not a real Google Cloud project. Auth listens on 127.0.0.1:9099; Firestore on 127.0.0.1:8081; emulator UI on 127.0.0.1:4000. Stop with Ctrl+C.

`npm run emulators:check` starts the emulators, verifies local responses and denial of direct Firestore client reads, and shuts them down automatically. These checks create no cloud resources. The Firebase wrapper selects the project-local Java runtime and emulator binary cache.

The backend selects FIRESTORE_EMULATOR_HOST=127.0.0.1:8081 and FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 by default in local mode and rejects non-loopback overrides. Server-side Firebase token verification and the operator allowlist protect private routes; denying direct client access is not sufficient server-side authorization.

## Codex MCP connection

For optional local Codex integration, open **Genesis itself** as the trusted VS Code/Codex workspace. A developer-owned `.codex/config.toml`, when present, starts the pinned Firebase MCP through the project wrapper, restricted to Auth/Firestore feature groups. This machine-specific configuration is excluded from source exports. Core Firebase tools remain available; approval prompts remain enabled. This is a local MCP setup, not an installation of the Firebase marketplace plugin.

Local configuration may contain this machine's absolute project path; adjust it after moving the checkout. A parent workspace may not load a nested Genesis configuration. Do not enable both this server and the official Firebase plugin for the same project.

`npm run mcp:check` tests initialization and tool discovery only. It does not invoke tools, authenticate a user or verify a cloud connection. A successful smoke check does not mean this running chat has loaded the new server.

## Cloud access: gated until credits are verified

Optional `AGENT_PROFILES_JSON` pins per-agent thinking, temperature and output limits in immutable configuration. The [profile example](config/agent_profiles.json) uses one primary model for all four model roles; its model name is a preparation value requiring the same explicit model/location verification as `GEMINI_MODEL`. Blank configuration uses the primary model automatically. A custom profile cannot authorize another model, and malformed settings fail closed. Cloud deployment with AI disabled needs no model key or profile override.

Container files and a disabled deployment template are prepared; [deployment/recovery instructions](docs/deployment-recovery.md) distinguish the web image, one-shot local worker and private HTTP worker. Named task dispatch, signed task identity verification, a 300-second lease and bounded 240-second child process are implemented and checked locally. The shared gateway's cloud SDK branch is prepared behind verified model/location/credit gates; actual cloud model execution, authentication/pricing and Cloud Tasks delivery/IAM remain unverified. `python -m backend.container --check` validates the web launch settings without connecting to services. Container builds remain unverified because this workstation has no Docker/Podman engine. These artifacts do not authorize deployment or service creation.

Local verification and known evidence gaps are recorded in [the evaluation record](docs/evaluation-record.json), with [reproduction instructions](docs/evaluation-evidence.md). Its source fingerprint and actual JUnit results establish local checks; `release_ready` remains false until genuine investigation, human review, A5, held-out and release evidence are supplied.

Evolution preparation is private and explicit: create an analytical snapshot with `POST /api/operator/evolution/snapshots`, then queue A5 with `POST /api/operator/evolution/runs` and its `snapshot_id`. A genuine human feedback event is required; repeating a snapshot returns its existing run. The same one-shot worker processes queued A5 work under the daily controls. Read the validated result at `/api/operator/evolution/runs/{run_id}`. An insufficient-evidence result creates no detector proposal.

The Evolution lab exposes these actions after operator sign-in, with stored history, actual review-count gates, shared usage detail, review notes and explicit candidate/held-out confirmations. Refresh reads authoritative state and preserves draft notes; there is no polling. Completed private investigations show the validated brief and citations before feedback is enabled. Browser tests intercept consequential success fixtures; they never manufacture genuine application evidence.

Candidate freezing and simulation are separate operator POST actions under `/api/operator/evolution/freezes`. Freezing requires a genuine A5 result and the reviewed candidate hash; insufficient feedback remains labeled. Only one detector selection can be frozen for this dataset. Simulation never activates it, and repeated requests return the stored state/result. No real A5 result or held-out comparison has been produced yet; these endpoints are implementation preparation.

Local Gemini integration is opt-in and uses the Developer API, independently of cloud deployment. With the local emulators running, `scripts/with-gemini-secret.ps1 -Action Api -EnableLocalGemini` starts the API with the pinned key held only in process memory. A separate `scripts/with-gemini-secret.ps1 -Action Worker -EnableLocalGemini` drains at most 100 queued parent jobs once, then exits. These commands access Secret Manager; the worker can make real requests only while today's admin switch is enabled and verification remains valid. Do not include them in automated tests. Further live investigation calls require the agreed bounded test approval.

Opt-in expires after one hour; new UTC days start disabled. Local testing uses the configured daily admin limit, up to 120 attempts, without a separate 12-attempt ceiling. Each alert has three model legs, each allowing at most one confirmed transient retry, plus token pre-count requests. Retry needs explicit short provider RetryInfo without quota details; every sent retry reserves a separate slot. Operators refresh explicitly. A provider timeout remains UNKNOWN_OUTCOME and blocks later legs; the one-shot worker never reclaims unleased RUNNING jobs. Managed delivery resumes sealed work only after its lease expires, with no resend of unknown attempts. Disable today's switch before inspecting recovery. Cloud delivery/deployment remain pending.

After local setup, interactive account sign-in and verification of a real credited project are still needed. Do not run initialization that creates/selects projects by guesswork.

When explicitly ready to sign in:

```powershell
npm run firebase -- login
npm run gcloud -- auth login
npm run gcloud -- auth application-default login
```

Firebase login uses the CLI's user credential store; never commit credentials. The gcloud wrapper keeps its local configuration under `.tools/gcloud-config`. Do not print credential files or access tokens.

Free tooling and confirmed credits only. No paid subscriptions, billing upgrades, live Gemini calls or cloud resources are approved by running these local checks. Verify the credit balance, expiration and eligible services first; budget alerts are not guaranteed spending caps.

## Local source export

The [local integration handoff](docs/local-integration-handoff.md) documents the offline source publisher, reviewed rate-card configuration, matching-source verification and optional genuine reference capture. All cloud actions remain gated; normal checks do not access cloud or a model.

After the unit/emulator reports and evaluation record match the current sources, run `python -m scripts.export_source` from Genesis using the project environment. It creates a deterministic source-only ZIP in ignored `.cache/release/`, containing the Genesis directory and a checksum manifest. Application sources, locks, tests, selected project docs/configuration and design context are allowlisted; internal `context/`, local agent configuration, credentials, environments, build output, logs and emulator evidence are excluded. Linked paths and recognized credential patterns abort export. The source fingerprint must still match verification before writing.

The archive is labeled PREPARATION_ONLY with release_ready false. It does not publish, initialize a repository, grant a license, deploy, submit or establish genuine investigation/evaluation evidence. Final publication destinations, rights, genuine runs, PDF and video remain release gates.

## Design and persistence

Project UI conventions are recorded in [DESIGN.md](DESIGN.md) and [UX-CONTRACT.md](UX-CONTRACT.md). Internal planning sources stay outside the application and are excluded from public artifacts.

Firestore stores immutable source/configuration/public snapshots and private execution, usage and feedback records. Emulator success does not prove production composite indexes or IAM are deployed. The source manifest and nine detector rules remain frozen; model recommendations cannot activate changes.

The future target is `genesis-aicb` (project number `638299117256`). Credit balance and expiration are unknown. This does not change the safe local demo-project defaults.

## Setup verification — 15 October 2026

- Verified Node.js 22.7.0, Firebase CLI 15.34.0, Google Cloud SDK 589.0.0, Temurin Java 21.0.12.1 and CPython 3.12.15.
- Firebase MCP initialize/tools-list smoke check passed. No cloud tools invoked.
- Auth/Firestore local emulator check passed; direct Firestore client reads denied; emulators shut down.
- No real Firebase project selected, cloud resources created, billing upgraded or live model calls made.
- Codex must load the Genesis workspace configuration before its MCP tools are available in a new session.
- Account sign-in and credit verification remain prerequisites for live Google Cloud work.

See [Evolution rule intelligence](docs/evolution-rule-intelligence.md) for Discovery access, separate advisory scores, aggregate publication and evidence-gated A0 learning.
