# Cloud connection vault: guided setup

> Completion audit ? 18 October 2026: The existing testing_free_gemini_api secret, metadata and payload-suppressed local access have been verified; web/worker/task identities exist. Do not create another illustrative test secret. Complete cloud runtime access and billing coverage remain separate acceptance checks.

## Current state — 16 October 2026

Latest key rotation: version 1 is now destroyed; metadata confirmed version **2** enabled. The reader defaults to pinned version **2**, not `latest`. One explicitly approved Developer API smoke test using version 2 passed (74 provider-reported tokens), and its local live switch was disabled afterward. No deployment occurred. The earlier version-1 access below is historical evidence.

The user created `testing_free_gemini_api` in `genesis-aicb` and supplied its value through the console. Project-local CLI sign-in is verified; metadata reads confirmed version **1** is **enabled**. After the user confirmed available shared Secret Manager free allowance, one payload-suppressed access check succeeded. The key was captured only in the check process and was not printed or written to a file. No Gemini request or deployment occurred. The earlier suggested name `genesis-gemini-api-key` does not exist; reuse the user's existing secret.

`scripts/with-gemini-secret.ps1` defaults to this existing secret and pinned version. Its default `Check` action captures the payload in process memory and reports only pass/fail and the resource reference. It restores the previous environment value on exit. The access check is complete; do not repeat it routinely. Gemini Developer API Free Tier and available Secret Manager allowance are independently user-confirmed; cloud inference/deployment credit coverage remains unverified.

```powershell
# From Genesis, after confirming available Secret Manager free allowance:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/with-gemini-secret.ps1 -Action Check
```

The setup helper is plan-only by default. Do not run it to create another secret now that the existing secret is identified. The historical preparation instructions below describe the original plan; the current state above supersedes their not-provisioned/sign-in status and suggested smoke-test secret.

Verified against Google documentation on 15 October 2026, Australia/Sydney.

Target: **genesis-aicb**, project number **638299117256**. This guide and the connection inventory are prepared; no cloud vault, secret, service account, API enablement, IAM grant or cloud deployment has been created by this task. Funding remains unverified. The local CLI has no active signed-in account in its project-local configuration.

## Design

Use **Google Cloud Secret Manager** as the single secret store. Secret Manager organizes secrets inside a project; there is no separate vault container to create. `genesis-` is our naming prefix, not a separate resource. Gemini uses this same store if an API key is eventually needed.

For the planned managed Google Cloud Gemini route, use Application Default Credentials locally and attached service accounts on Cloud Run. Firestore also uses identity/IAM, rather than a database password. Do not create service-account JSON keys just to populate a vault.

| Connection material | Where it belongs |
| --- | --- |
| Project ID/number, regions, model ID, service URLs, Firebase web configuration | Non-secret deployment configuration; inventory in `config/cloud-connections.example.json`. |
| Gemini managed Google Cloud access | Local ADC; attached worker service identity in deployment. No Gemini key required for this route. |
| Firestore access | Backend service identity and IAM; never a browser database password. |
| Cloud Tasks delivery | Queue caller service identity and short-lived OIDC authentication. |
| Operator login | Firebase Auth; backend verifies user ID token and allowlisted UID. Do not put passwords in Secret Manager for this workflow. |
| Third-party API key, if later selected | Its own Secret Manager secret. Grant only the consuming service access. |
| Gemini Developer API key, only if that alternative is chosen | `genesis-gemini-api-key`; optional, currently not selected. |
| Prompts, skills, scoring policies | Versioned source/config, not credential payloads. |
| Per-leg usage, evaluations, feedback, audit events | Application records in Firestore; no secret values in audit records. |

The inventory is documentation, not an application configuration loader. Do not change local defaults to the real cloud project yet.

## Step 1 — Check the project and funding

1. Open [Google Cloud Billing for genesis-aicb](https://console.cloud.google.com/billing?project=genesis-aicb).
2. Confirm the selected project is **genesis-aicb**. Check its linked billing account, if any.
3. Inspect the billing account's credit details, remaining balance, expiration and applicable services. Navigation wording can vary; credits may appear under the billing account overview or credits pages.
4. Check existing Secret Manager usage across that billing account, since its free allowance is shared across projects.
5. Record only whether billing is linked and what allowance/credits are available. Do not send payment details, account credentials or secret values.

If billing is absent, credits are expired, or allowance cannot be verified, stop at this step. Do not upgrade billing or start a subscription to continue. We can keep preparing locally.

### Free allowance and limits

Google currently lists **6 active secret versions**, **10,000 access operations** and **3 rotation notifications** free per month, aggregated by billing account. Both enabled and disabled versions count as active. Automatic replication is billed as one location. Exceeding the allowance can incur charges; this is not a hard spending cap.

For this prototype, start with one harmless test secret/version, no rotation notifications, no Pub/Sub integration and no repeated polling. Do not upload duplicate versions on every build. Actual credential access will be backend-only, with pinned version references when deployed. Historical disabled versions still consume allowance; destruction is irreversible and needs an intentional cleanup decision.

## Step 2 — Open Secret Manager, after Step 1 passes

Open [Secret Manager for genesis-aicb](https://console.cloud.google.com/security/secret-manager?project=genesis-aicb). If the API is disabled, enable **Secret Manager API** after confirming Step 1. This does not require enabling every Google service or deploying the app.

The setup operator needs permission to create secrets; `roles/secretmanager.admin` is an administrative setup role, not an application runtime role. Use an existing authorized project administrator for setup where possible. Do not grant broad roles to the application.

## Step 3 — Create a harmless smoke-test secret

After funding/allowance verification:

1. Choose **Create secret**.
2. Name: `genesis-vault-smoke-test`.
3. Value: `genesis-vault-smoke-test-v1` (deliberately not a credential).
4. Use automatic replication for this synthetic connectivity check. Real regulated-data residency is a separate production decision.
5. Leave rotation scheduling, rotation notifications and customer-managed encryption unset for this check; use Google-managed defaults.
6. Create once, then confirm version **1** exists and is enabled.

Do not create empty placeholder Gemini/database secrets. Our intended connections are keyless, and unused versions only add maintenance and allowance usage.

## Step 4 — Verify in the console first

Open the test secret and confirm its name, project, replication setting, and version status. An authorized person may view its harmless test value in the console. Do not share real secret payloads in chat, screenshots, terminal logs or repository files.

At this point the secret store is initialized. Its future reference is:

```text
projects/genesis-aicb/secrets/genesis-vault-smoke-test/versions/1
```

This is an identifier, not a secret value.

## Step 5 — Connect the project-local CLI

Run from **Genesis**, only when ready for interactive sign-in:

```powershell
npm run gcloud -- auth login
npm run gcloud -- secrets describe genesis-vault-smoke-test --project=genesis-aicb
npm run gcloud -- secrets versions describe 1 --secret=genesis-vault-smoke-test --project=genesis-aicb
```

The wrapper keeps Cloud SDK configuration in ignored `.tools/gcloud-config`. Explicit project flags avoid changing the safe local application's project. The describe commands inspect metadata and do not print a secret payload. This metadata check does not prove runtime secret access.

We will add the local application ADC connection and a payload-suppressed access test next. CLI login and ADC login are separate. Do not paste sign-in authorization codes or tokens into this chat.

## Step 6 — Give runtime identities narrow access

Before migration, provision separate web/API and worker service identities. Grant `roles/secretmanager.secretAccessor` on an individual secret only to the service that needs its payload. The web service does not need an optional Gemini API key if the worker is the only model caller. Neither service receives Secret Manager Admin.

Google Cloud Gemini, Firestore and Cloud Tasks permissions are separate IAM grants, not secret values. Select those roles during service provisioning. Do not store service-account JSON keys, access tokens or copied ADC files in Secret Manager.

## Step 7 — Migrate references and test one connection at a time

1. Verify secret access using the intended identity, recording pass/fail and version reference without printing the payload.
2. Wire the deployment to an explicit secret version only if a real secret is required. Do not put secret payloads into `VITE_*` variables or the browser bundle.
3. Verify Firestore access separately, then authenticated worker delivery.
4. Verify Gemini credit coverage and quota separately before one bounded live model call. Secret Manager's free allowance does not make Gemini inference free.
5. Register connection checks as metadata-only audit events. Record actor/service identity, resource/version ID, UTC time, result and request ID; never payloads.
6. Enable live AI only after those checks and the invocation limit/kill switch are implemented and verified.

These are later stages, not actions to run simultaneously with Step 1. The existing emulators remain available throughout.

## Progress

- [x] Choose the single secret store and keyless-first connection approach.
- [x] Prepare a non-secret connection inventory inside Genesis.
- [ ] Verify billing account, credits and shared free allowance.
- [ ] Enable Secret Manager API if needed.
- [ ] Create the one-version harmless test secret.
- [ ] Verify console and CLI metadata.
- [ ] Provision runtime identities and scoped access.
- [ ] Verify payload-suppressed runtime access.
- [ ] Connect and test each application service.

## Official references

- [Secret Manager pricing and free allowances](https://cloud.google.com/secret-manager/pricing)
- [Create a secret](https://docs.cloud.google.com/secret-manager/docs/creating-and-accessing-secrets)
- [Secret Manager IAM](https://docs.cloud.google.com/secret-manager/docs/access-control)
- [Access a secret version](https://docs.cloud.google.com/secret-manager/docs/access-secret-version)
- [Cloud Run service identity](https://docs.cloud.google.com/run/docs/securing/service-identity)
- [Google Cloud Gemini authentication quickstart](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart)
