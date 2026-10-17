# Deployment and recovery preparation

## Current private update - 17 October 2026

Build `0d25fbe5-add3-466c-895f-6e2325c71a94` succeeded for tested source `efd33c4f51cc7bf69a72a3360221f940a06087afe407bd6d25ec5aecb083f873`; both image digests and isolated smokes are verified. Web digest: `sha256:8529077b16924c006da11db7151c5d6c1b26d6d656bc340ab3ea4917b458f7cb`. Worker digest: `sha256:a8b5236e203cea149605b2c2892b8e3caec2952e66ad67ed87e40f0041f32fc6`. Both remain in Sydney's `genesis-demo-images` repository.

Actual ready revisions are `genesis-demo-web-00003-v25` and `genesis-demo-worker-00004-5b9`. Readback verifies source/image identity, scale 0–1, original runtime service accounts, private IAM, unchanged Google UID allowlists and disabled cloud AI/task switches. Signed-out HTTP is 403; authenticated health is 200; task queue is PAUSED. Independent receipt: `.cache/deploy/private-staging-verification-efd33.json`. Prior 558ac images/revisions below remain the rollback baseline; do not rebuild or delete them as recovery.

The installed native `gcloud run services proxy` exposes this private web service only at `http://127.0.0.1:18082`. Its [upstream implementation](https://github.com/GoogleCloudPlatform/cloud-run-proxy/blob/main/main.go) supplies IAM authentication in `X-Serverless-Authorization`, preserving application Firebase Authorization. Browser verification saw the deployed Google control, missing-Firebase-session 401 and unpublished-cases 503. The user then confirmed Operator login, corroborated by deployed session HTTP 200 logs on the current web revision. Local emulator app remains separate at port 8080 with its genuine investigation/review records. Cloud source publication, AI/task activation and public access are not authorized by the private update.

## Verified private staging - 17 October 2026

This section supersedes the historical undeployed snapshots below. Replacement build `a8278142-5a7e-4a24-a90d-df32f5aa780b` succeeded for source `558ac42410d2eb7d9a84056cc0aa33c24e54e48e396a76107cc9e4f00c789148` (82 unit / 11 fresh-emulator integration passes). Web image digest is `sha256:9b637e8a9a43f77dbd7fca7133ed3f7b0594b87e6b0ad2d924709c0c7a28a36f`; worker is `sha256:584da09ad0fbf89a0bd8388235385261d30bb5c4e7208432181418607dab0080`, both in the Sydney `genesis-demo-images` repository.

Private services `genesis-demo-web` revision `genesis-demo-web-00002-22x` and `genesis-demo-worker` revision `genesis-demo-worker-00003-fv2` passed readback of pinned images, runtime identities, min 0/max 1 at service and revision level, IAM invocation checks and absence of public bindings. Both deny signed-out HTTP requests with 403; authenticated web health returns 200. Queue remains PAUSED; all live-AI, local-Gemini, credits and task switches remain false. Firebase Google provider, Google-linked operator UID allowlists and web authorized domain are configured. No public source data, genuine investigation or browser Google-login evidence is claimed. Private receipts are `.cache/deploy/private-staging-verification.json` and `.cache/deploy/staging-558ac42410d2eb7d.json`.

Keep these pinned images as the verified staging baseline. The new Google UI is a later local source change and needs its own verified package and separate build approval. Do not reuse the consumed one-build authorization, enable AI/tasks, publish data, or make either service public as a recovery shortcut. Image vulnerability scanning remains pending.

## Updated source and resource reconciliation - 17 October 2026

The user reported application changes and additional cloud resources. Native CLI checks reconfirmed the existing project, SDK 589.0.0 and an active local login. Cloud Run listing across regions returned no services. Nine sanitized metadata reads succeeded: Sydney queue PAUSED and one Docker repository; project-wide one Firestore database, one secret name, one staging bucket, six service accounts and 50 enabled APIs; Cloud Asset Inventory returned 77 indexed assets. Those assets include two monitoring dashboards ("Cloud Observability Overview" and "New Dashboard - Oct 17, 2026 1:32 PM"), Firebase rules and browser-key metadata. Asset indexing is eventually consistent; no secret values or API-key strings were read. Existing scoped build/runtime grants and private Sydney bucket settings were read back successfully. Private receipts are `.cache/deploy/resource-inventory-20261017.json` and `.cache/deploy/deployment-preflight-20261017.json`.

Current application source fingerprint is `afaa79bb9e71047c64a91bb67c96c7558e432874947d9bd7611fc6d0745b1e00`. The new per-agent generation profiles initially weakened verified-model checks, introduced an unsupported thinking value, and allowed mutable execution parameters outside the frozen bundle. These issues were corrected: model/location authorization remains exact; custom profile choices do not grant model access; full model/thinking/temperature/output-cap settings and request hashes are immutable and rechecked before reservation. Legacy bundles retain their original exact-model defaults. The interim local Free Tier remains restricted to its verified model. No real provider request was made.

Matching verification currently records **81 unit passes and 11 fresh-emulator integration passes, zero integration skips**, plus production build and full application browser journeys. The unit command's 11 default emulator skips are separately exercised by the explicit integration run. Infrastructure dashboards belong in Google Cloud Console; no resource-management dashboard is part of the Genesis application.

The earlier successful build below remains bound to `6cd03b64...`, not this updated source. Its digests and one-use approval must not be relabeled or reused as verification of the current revision. Prepare a fresh immutable candidate and request a separate bounded build/staging authorization before submitting another build or deploying services. Source publication, public access, operator setup, funding/model coverage and live investigations remain separate gates; the AUD 6 alerts-only budget is not a hard cap.

## Verified build and image push - 17 October 2026

The user explicitly approved **one Cloud Build and image push within the AUD 6 monthly plan**, replacing the earlier no-spend restriction for this operation only. Resources were declared, configured and read back before the exact 48-file source allowlist was uploaded. Cloud Build **[fbca029c-cde5-41a3-9eba-99dee9b03e54](https://console.cloud.google.com/cloud-build/builds;region=australia-southeast1/fbca029c-cde5-41a3-9eba-99dee9b03e54?project=638299117256) succeeded**, with all four steps passing: package verification, web build, worker build and network-isolated container smoke checks. Execution lasted 118.60 seconds (14:35:49-14:37:47 AEDT, Sydney). No second build was submitted.

| Resource | Verified value / boundary |
| --- | --- |
| Project / region | `genesis-aicb` / `australia-southeast1` |
| Build API | `cloudbuild.googleapis.com`, enabled for the approved build |
| Build identity | `genesis-demo-build@genesis-aicb.iam.gserviceaccount.com` |
| Scoped permissions | Project `logging.logWriter`; repository `artifactregistry.writer`; staging bucket `storage.objectViewer` |
| Managed build agent | `service-638299117256@gcp-sa-cloudbuild.iam.gserviceaccount.com`, managed `cloudbuild.serviceAgent` role read back |
| Source staging | `gs://genesis-aicb-build-source-638299117256-syd`, same project, Sydney Standard storage |
| Staging privacy/retention | Uniform access, public access prevention enforced, soft delete disabled, source objects deleted by lifecycle after one day |
| Build bound | One `E2_STANDARD_2` build, 1200-second timeout, no automatic resubmission |
| Image repository | `australia-southeast1-docker.pkg.dev/genesis-aicb/genesis-demo-images` |

Both immutable image references were read back from Artifact Registry and match the build results:

```text
australia-southeast1-docker.pkg.dev/genesis-aicb/genesis-demo-images/web@sha256:9723ec4321f4596b91fa4a13e7849aac94198829e1567844e5593c58daa8457f
australia-southeast1-docker.pkg.dev/genesis-aicb/genesis-demo-images/worker@sha256:2b52821c35989a47849a58430e3a23b4822b51c85c3532d7fe5ed42645c31658
```

The images use tested source fingerprint `6cd03b64cc2d6616ee4ba4465c301453520c5a4bf572ff7b63e49549ccbaf426`, base Git revision `c5595b958896c93455bc57bd60cfc6e70292e2dd` with uncommitted changes. A source fingerprint/image digest is not a release commit. Existing native evidence remains 70 unit and 11 fresh-emulator integration passes, plus frontend build/browser checks; application sources did not change for this build.

Actual image checks establish UID/GID 65532, startup, web health/static frontend, signed-out private web/worker denial, and disabled AI/task/credit switches. The smoke containers had no network and no model key. This is real Linux container evidence from the approved Cloud Build route; a local Docker/Podman engine is still absent. Image vulnerability assessment is not run; passing startup is not a security scan or proof of deployed IAM/OIDC, Firebase sign-in, real database/investigation or model operation.

Published compute list-rate estimate for the measured duration is approximately **US$0.01186 before free allowances**, excluding separate storage/registry/logging/network costs. Actual billed cost/remaining budget is not returned by the build response. The AUD 6 budget is alerts-only and was not changed. No cloud credits or model coverage were inferred or enabled.

Cloud Run service inventory in Sydney remains empty. The task queue is verified PAUSED. No app deployment, source-data publication, live model request, secret read or operator account creation occurred. Private receipts: `.cache/build/build-push-verification.json`, `.cache/build/cloud-build-setup.json` and `.cache/deploy/built-images.json`. These image references are ready for a separate reviewed Cloud Run deployment; runtime/Auth/model/funding and genuine workflow gates still apply.

## Provisioned foundation — 17 October 2026

After preflight, the user explicitly instructed: "let's start creating resources and we will figure this on the way". This supersedes the earlier funding-first and M1-first ordering for foundation creation. Credit coverage remains UNVERIFIED; no `CREDITS_VERIFIED` or live-generation flag was enabled. Use the existing native gcloud wrapper and APIs, with no new provisioning framework.

Created in project `genesis-aicb` / `638299117256`:

| Resource | Actual value / observed state |
| --- | --- |
| Region | `australia-southeast1` (Sydney) |
| Firestore | `(default)`, Standard / Native mode, deletion protection enabled; provider reports `freeTier: true` |
| Rules | `projects/genesis-aicb/rulesets/2fe9b038-2e0d-46f6-95d3-5f2b7f33ccf5`, released as `cloud.firestore`; exact match to repository deny-all source |
| Composite indexes | All 13 verified `READY` |
| Field index exemptions | All 14 submitted and read back with no indexes configured |
| Registry | `australia-southeast1-docker.pkg.dev/genesis-aicb/genesis-demo-images`, Docker format, no images uploaded |
| Task queue | `projects/genesis-aicb/locations/australia-southeast1/queues/genesis-demo-triage`, verified `PAUSED`; concurrency 1, rate 1/s, 3 delivery attempts, backoff 310–600 seconds |
| Firebase web app | `genesis-demo-web`, app ID `1:638299117256:web:6f36170a6efba49d5cb7fd`, ACTIVE |
| Runtime accounts | `genesis-demo-web@genesis-aicb.iam.gserviceaccount.com` and `genesis-demo-worker@genesis-aicb.iam.gserviceaccount.com` |
| Task account | `genesis-demo-tasks@genesis-aicb.iam.gserviceaccount.com` |

Enabled the required Run, Artifact Registry, Firestore, Cloud Tasks, managed model (`aiplatform.googleapis.com`), Identity Toolkit, IAM Credentials, Firebase and Firebase Rules APIs. Firebase was added to the existing project, not a new project. API activation also created Google's default Compute Engine service account; it is not used as an application runtime identity.

Applied project roles: web → `datastore.user`, `firebaseauth.viewer`; worker → `datastore.user`, `aiplatform.user`. Web has `cloudtasks.enqueuer` on this queue only and `iam.serviceAccountUser` on the task account. Google's actual Tasks service agent has its managed `cloudtasks.serviceAgent` project role and `iam.serviceAccountUser` on the task account. Worker-scoped `run.invoker` will be assigned to the task account only after the worker exists. No runtime Owner/Editor grant or service-account key was created.

Verified anonymous database read returns HTTP 403, deployed rules match source, and queue is paused. Sanitized evidence is in ignored `.cache/deploy/foundation-verification.json`. The Firebase CLI's stale login returned 401; Firebase registration/rules used the working gcloud identity through official APIs with explicit `x-goog-user-project: genesis-aicb`. Access tokens stayed in process memory.

Remaining before application deployment: local container build/execution, reviewed cloud data publisher, real operator/admin identities and Auth provider/key/domain setup. No Cloud Run service, application data, public URL or model request exists from this foundation task. Funding and model verification remain separate unfinished records; the US$10/month estimate is not an enforced cap.

## Infrastructure preflight — 17 October 2026

Read-only checks using the existing project-local gcloud wrapper confirmed:

- Project `genesis-aicb`, number `638299117256`, is ACTIVE; the existing CLI account is signed in.
- Secret Manager, logging, monitoring, Service Usage and Cloud Storage APIs are enabled.
- Firestore, Cloud Run, Artifact Registry, Cloud Tasks, `aiplatform.googleapis.com`, Firebase and Identity Toolkit APIs were absent from the enabled-service inventory. Do not infer that application infrastructure is ready from the enabled Datastore API.
- The service-account list returned no accounts. Firestore, Cloud Run and Artifact Registry resource listing failed with `SERVICE_DISABLED`; resource absence was not independently established.
- Neither Docker nor Podman was found on PATH. No cloud publication implementation was found in `scripts/` or `backend/`; the existing seeder remains emulator-only.

The user requested starting Google infrastructure setup with Ponytail. This authorizes work toward setup, but supplies no new credit coverage or paid-spend limit. Funding evidence has been requested. No API was enabled, resource provisioned, IAM changed, image uploaded, data published or model called during this preflight.

Next: verify funding/allowances and the approved usage window; complete local container execution and the reviewed cloud publisher (M1); then apply the existing resource guide with actual locations and identities. Reuse its proposed resource names and native gcloud commands rather than introducing another provisioning framework. Keep live AI and task dispatch disabled. The earlier US$10/month demo estimate is a planning allowance, not verified funding or an enforced cap.

The [step-by-step HTML setup guide](../submission/deployed-prototype/resource-setup-guide.html) translates this contract into resource naming, dependencies, IAM/configuration examples, phased deployment and integration checks. It is a local runbook; commands are documented rather than executed. Its proposed resource names do not replace verified configuration, and cloud source publication remains a separate implementation checkpoint.

Cloud operator sign-in preparation uses `FIREBASE_WEB_API_KEY` for the intended Firebase web app, separate from private model credentials. Configure only a verified Firebase-specific key with appropriate API/origin restrictions; never expose the Gemini key. The public config response returns it only in cloud mode. Email/password provider availability, authorized domains, actual user identities/allowlists and a signed-out-to-operator deployed journey must be checked before release. No account/provider/key is created by this code. Missing configuration keeps sign-in disabled with explicit retry; credentials and ID tokens stay out of browser storage and URLs. The Google REST request uses the public Firebase project key in its documented query parameter; user credentials are sent only in the JSON body.

Status: foundation provisioned as recorded above; application deployment remains pending. [deployment.example.json](../config/deployment.example.json) remains a disabled template, not a record of actual resources. A passing local check does not enable live execution.

## Artifacts and local checks

The Dockerfile builds the frontend with the existing npm lock and backend dependencies with the existing uv lock, excluding Python development packages. The runtime contains only the backend, its environment and (for web) built static assets. The build-context allowlist excludes `context/`, credentials, caches, logs, emulator exports, local tools and environments. Runtime UID/GID is 65532; no credential or Gemini key is baked into an image. This follows [uv's documented multistage approach](https://docs.astral.sh/uv/guides/integration/docker/).

Node 22.7.0 and Python 3.12.15 base-image tags were verified through public Docker Hub metadata, including Linux amd64 availability, and pinned to returned manifest digests. The uv 0.13.1 registry manifest was also verified for Linux amd64 and pinned. Image execution, final image digests and base-image vulnerability assessment remain pending. Docker/Podman is not installed on this workstation; do not count static/runtime-option checks as a successful container build.

When a local Linux container engine is available, run from `Genesis/`:

```powershell
docker build --platform linux/amd64 --target web -t genesis-web:local .
docker build --platform linux/amd64 --target local-worker -t genesis-local-worker:local .
docker build --platform linux/amd64 --target worker -t genesis-worker:local .
```

These commands do not push an image or deploy a service. The `local-worker` target is a one-shot emulator worker and requires loopback access to the emulators; arbitrary host overrides remain rejected. Do not deploy that target as a Cloud Run service. The separate `worker` target exposes only the authenticated task handler. Actual Cloud Tasks delivery, deployed identity verification and cloud model execution remain pending.

`python -m backend.container --check` validates startup settings without importing the API, starting HTTP or connecting to services. Local mode stays on 127.0.0.1. Cloud mode validates an explicit real-project setting and binds 0.0.0.0 at `PORT`, as required by the [Cloud Run runtime contract](https://docs.cloud.google.com/run/docs/container-contract). The Docker web target defaults to cloud mode with live AI disabled and fails startup without a project. Native local development remains `npm.cmd run api`. A cloud runtime check is not evidence of valid credentials or funding.

## Private worker and IAM review

Before any deployment, verify actual coverage for Gemini/Vertex, Cloud Run, Firestore, Cloud Tasks, build and artifact storage; choose the supported region/model and confirm operator/admin UIDs. Do not enable a service or billing account based on this template. Cap scaling at the reviewed instance/concurrency settings, but do not treat them as a guaranteed spending cap.

The intended worker must be a separate private service with no public invoker binding. Cloud Tasks delivery uses an OIDC token whose audience is the verified worker service URL. Its invoker service account must belong to the queue project and have Cloud Run Invoker on the worker. Verify the Cloud Tasks service-agent/token permissions and enqueuer permissions against [Google's authenticated HTTP task instructions](https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks). Keep the web runtime, worker runtime and task invocation identities distinct; confirm scoped Firestore access and attach runtime identities rather than shipping service-account keys. These bindings are a review checklist, not configured resources.

The private HTTP handler is `POST /internal/jobs` with only `run_id` and integer `generation`. Startup requires cloud mode, an HTTPS `WORKER_AUDIENCE` origin and same-project `TASK_INVOKER_EMAIL`. It verifies a Google-signed ID token's audience, issuer, expiry, exact email and verified-email claim before creating a Firestore client. Use the `Authorization` header: Google's [Cloud Run authentication instructions](https://docs.cloud.google.com/run/docs/authenticating/service-to-service) state that `X-Serverless-Authorization` has its signature removed before forwarding. Task-name headers alone grant no access. This application check supplements private Cloud Run IAM; no IAM bindings have been applied.

Delivery claims a fenced 300-second lease and starts the shared runner in a separate subprocess, bounded to the remaining 240-second execution budget. Busy leases return a retryable 503; stale/terminal deliveries acknowledge without execution. Timeout kills/waits for the child, keeps durable checkpoints/unknown attempts and permits safe recovery only after lease expiry. The queue dispatch deadline and service request timeout must be 300 seconds, leaving cleanup time beyond the child bound. Queue redelivery never repeats a STARTED/unknown provider attempt.

The worker permits one linked retry only for a confirmed 429 RESOURCE_EXHAUSTED rejection carrying exactly one short RetryInfo (at most five seconds) and no quota/billing/other failure detail. It waits at least the provider delay, then recounts the same input and rechecks authorization, switch, cap and lease. The second attempt has its own immutable ID, retry link and atomic reservation; the transaction checks the first rejection, matching configuration/input and minimum wait. Bare 429s, quota failures, credit/cap refusal, long delays and unknown outcomes do not retry. Completion, private reads and candidate freeze follow the validated linked attempt instead of assuming attempt one succeeded. The SDK itself never retries. This deliberately conservative policy follows Google's [RetryInfo minimum-wait contract](https://github.com/googleapis/googleapis/blob/master/google/rpc/error_details.proto).

The dispatcher persists a hashed task ID/generation before transport and calls CreateTask outside transactions, with SDK retries disabled and a ten-second timeout. It sends only run ID/generation, a 300-second deadline and OIDC identity/audience. Unknown sends retain the same task identity; an explicit repeat can acknowledge ALREADY_EXISTS without generating another ID. A known SENT state does not call CreateTask again. Known configuration/permission failures are separate from unknown outcomes. Task acknowledgements indicate delivery ownership, never successful model execution. The algorithm follows Google's [CreateTask deduplication contract](https://docs.cloud.google.com/python/docs/reference/cloudtasks/latest/google.cloud.tasks_v2.services.cloud_tasks.CloudTasksClient#create_task).

A confirmed send rejection leaves the investigation QUEUED with DISPATCH_FAILED as its error and FAILED as its dispatch outcome. Children remain queued; no terminal parent/child result is invented. An explicit enqueue repeat returns the same active batch, prepares a new generation and preserves its child IDs/checkpoints. An unknown send always retains its existing identity. A later acknowledgement or actual delivery takes precedence over a concurrent send error.

Cloud enqueue requires `CLOUD_TASKS_ENABLED=true`, a same-project `TASK_QUEUE_PATH`, valid worker identity/audience, unexpired verified cloud credits/live mode and a verified model/location tuple. Default settings refuse before enqueue or client construction; expiry and model gates are checked again immediately before sending. These flags are deployment gates, not proof of coverage. No queue, IAM binding or live dispatch has been created or tested.

The shared SDK gateway now has a prepared cloud branch using explicit project/location and the stable v1 API, with no Developer API key argument or fallback. The installed google-genai 2.31.0 and current [official SDK documentation](https://googleapis.github.io/python-genai/) support `enterprise=True` (the legacy flag is `vertexai`). `VERIFIED_CLOUD_MODEL_ID` must match `GEMINI_MODEL`, and `VERIFIED_CLOUD_LOCATION` must be explicitly populated after G16 verifies support; there is no assumed location. Cloud calls require a worker lease before token pre-counting. The frozen bundle pins model, provider, location, prompts and attempt ceiling. Old bundles do not gain retries. The same validator/reservation/sealing path handles both transports. Cloud credentials are attached through ADC/runtime identity when actually enabled, not a shipped key. Constructor/fault tests do not establish live authentication, model availability or pricing. Cost stays UNKNOWN until an applicable rate card is verified. All real model/location fields in the deployment template remain null and all execution switches remain false.

## Operator recovery now

The shared local/leased runner now uses explicit generations and fenced 300-second claims with a 240-second execution deadline. Reservations reject stale ownership and require token-precount/transport/sealing headroom. Recovery preserves sealed checkpoints and marks abandoned STARTED attempts UNKNOWN_OUTCOME without sending again; late responses remain private observations on the same step. HTTP authentication, bounded execution and named dispatch are implemented locally. Actual Cloud Tasks delivery and deployed recovery remain unverified.

1. Disable today's live-AI switch in Admin before inspecting a stalled run. The server checks expected revision and reserved-attempt floor. Disabling stops new attempts; an already-sent request may still finish. Stop the one-shot worker process if it is still running.
2. Explicitly refresh the private alert/run usage. Keep each sealed step and its outcome. A terminal child failure remains part of the failed parent, including when other children completed.
3. A STARTED or UNKNOWN_OUTCOME provider step may have incurred usage. Never delete it, reset daily reservations, invent zero cost or automatically send it again. Keep unknown usage/cost visible. Schema/citation failures must not be converted to successful narrative output.
4. The one-shot local worker does not reclaim unleased RUNNING jobs. Managed delivery can reclaim only after its persisted lease expires, with the same generation; it validates every stored checkpoint and stops on unknown outcomes. Do not edit a parent back to QUEUED, delete attempts or mark a step COMPLETE. Until authenticated task transport is deployed and checked, preserve stalled work for inspection.
5. Export a new timestamped emulator snapshot if evidence must be preserved. Keep exports, prompts, operator notes and `.cache/gemini-smoke-20261016` private and excluded from publication. The existing connectivity export must not be overwritten.
6. A new UTC day starts disabled. Credit expiry is deployment configuration, not an admin-editable extension. Re-enable only after the recorded access/credit gate and the agreed bounded live test are approved.

## Publication boundary

The current seeder is restricted to local emulators and creates local fixture credentials. Do not run it against `genesis-aicb` or import its Auth fixture into cloud. The separate `backend.publisher` now prepares deterministic sources/configuration and publishes only public DEMO cases. Its default dry run is offline; apply requires reviewed funding/identity/source approval and disabled execution controls. See [the local integration handoff](local-integration-handoff.md). Actual cloud publication remains unexecuted by this code batch and requires real operator identities. Preserve the nine rules and original source manifest. Never copy private attempts, briefs, analyst notes, reference labels or missed-case IDs into a public snapshot.

Before release, record successful local container builds/image hashes, authenticated worker checks, genuine investigation/manual grounding/feedback/A5/frozen comparison, deployed revision IDs and signed-out URLs. The [evaluation record](evaluation-record.json) currently has these release fields missing and `release_ready: false`. Repository, deck, video and submission publication remain gated on their actual destinations, eligibility/cutoff and explicit release authorization.
