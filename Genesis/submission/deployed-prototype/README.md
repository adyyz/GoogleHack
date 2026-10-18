## UI revision after candidate preparation

The unified 40,000-transaction queue, 10,000-case reference walkthrough and queue-based review dialogs are newer than archive 4f0b3f719ea98955. The user instructed **do not build**; no replacement package, cloud build or deployment was performed for this revision. Candidates listed below are historical, not the current UI.

## Latest verified local candidate - 18 October 2026

The bulk-learning replacement is [genesis-build-candidate-4f0b3f719ea98955.zip](genesis-build-candidate-4f0b3f719ea98955.zip). SHA-256: `5248dcb0833dce8f9d8d0f184e52399929912c08fe2e7d951fc99abb3bfdf478`; source fingerprint `4f0b3f719ea98955e8234dacadbe289f96b86f89b2745162d1ca2defb173238b`.

114 unit and 20 isolated Firebase integration tests passed (zero integration skips), along with production build, browser journeys and strict design checks. Genuine bulk investigation, user-frozen review and A5 insufficiency were verified; synthetic annotations remain separate. Archive integrity and Cloud Build SDK schema passed.

**PREPARED_NOT_SUBMITTED**: no new cloud image/build/deployment, index application or bulk data publication. Existing private staging revisions remain unchanged. Public repository publication stays on hold. Earlier candidates below are historical.

## Current local replacement - 18 October 2026

The Evolution rule-intelligence candidate is [genesis-build-candidate-8cacba49b88ce5d1.zip](genesis-build-candidate-8cacba49b88ce5d1.zip). SHA-256: `f40a571425f0cfbae9f463d426730f341c17f6734843afd80d3875caf71a1ad4`.

Source fingerprint: `8cacba49b88ce5d1578a95869ce0795562b04d41d62b1cfb7ce8aeaf8150f31d`. Local checks: 108 unit passes, 16 isolated Firebase integration passes without integration skips, production build, browser journeys and strict design checks. Genuine investigation, user-frozen feedback and A5 v2 were verified locally. Learning remains insufficient (4 overall / 2 HIGH_VALUE reviews); no policy was applied.

Status: **PREPARED_NOT_SUBMITTED**. Archive integrity and Cloud Build SDK schema passed. The package includes reviewed Firestore index/rules files under `deployment/`; neither was applied to cloud. Existing image digests/revisions remain the deployed baseline. A new build/private-service update requires its separate spending gate, and Vertex/public repository publication remain gated. Internal context, credentials and evidence caches are excluded.

# Live deployed prototype

Required: a deployed prototype link that remains available throughout evaluation. Status: private staging deployed and verified; public release pending. Billing linkage alone does not verify funded coverage or authorize further execution.

Current source `efd33c4f51cc7bf6` passed 82 unit / 11 fresh integration tests, build and full browser journeys. Approved build `0d25fbe5-add3-466c-895f-6e2325c71a94` succeeded; current private revisions are web `genesis-demo-web-00003-v25` and worker `genesis-demo-worker-00004-5b9`. AI/tasks remain off. The public prototype acceptance box remains open. [Actual deployment and recovery evidence](../../docs/deployment-recovery.md) distinguishes this from older snapshots below.

Start with the [step-by-step HTML resource/setup guide](resource-setup-guide.html): naming inventory, dependency order, PowerShell command examples, IAM boundaries, cloud configuration, deployment checks and recovery. It is an offline reference, not a cloud installer. Proposed resource names and blocked source-publication work are explicit.

- [x] Prepare the resource naming and setup/deployment HTML runbook.
- [x] Prepare a verified-source build bundle for web and worker, with checksums and an offline integrity check. This does not establish successful image builds.

- [x] Track the existing disabled deployment preparation: [configuration](../../config/deployment.example.json) and [recovery instructions](../../docs/deployment-recovery.md).
- [ ] Verify funding/service coverage, cloud model/location, runtime identities and operator/admin access.
- [x] Build and push web/private-worker images in the approved Cloud Build; verify non-root startup, health/static frontend and private-access refusal.
- [ ] Complete image/runtime release checks and deploy Cloud Run only after its configuration/execution gates are cleared.
- [ ] Record actual deployed revision IDs and a working public HTTPS prototype URL.
- [ ] Check signed-out evidence/usage reads, operator sign-in and private output protection; verify the genuine workflow.
- [ ] Confirm the official evaluation availability window and the plan to keep the service healthy within verified coverage.
- [ ] Recheck the URL before submission and during evaluation; public browsing must not trigger model calls.

Public prototype URL: **Pending**.

Web/private-worker revision IDs: **`genesis-demo-web-00003-v25` / `genesis-demo-worker-00004-5b9` (private staging)**.

Evaluation availability window and health-check responsibility: **Pending**.

Access/recovery evidence: image smoke checks passed; deployed journeys pending. Build `fbca029c-cde5-41a3-9eba-99dee9b03e54`, [actual resource/image handoff](../../docs/deployment-recovery.md).

## Local build package - 17 October 2026

Package: `genesis-build-package-89f5c10f20997a67.zip`, companion `genesis-build-package-89f5c10f20997a67.zip.sha256`. SHA256: `89f5c10f20997a67553de76a8700e18cb84a3ae420b0764fae16b4686253c79a`.

The bundle contains 40 exact runtime/build-context files from the verified source, plus a README, manifest, offline verifier and Google Cloud Build JSON template. It excludes private context, environments, credentials, local evidence and submission binaries. Its fingerprint is `6cd03b64cc2d6616ee4ba4465c301453520c5a4bf572ff7b63e49549ccbaf426`, matching the 70 unit / 11 emulator integration passing record. App code and dependencies were not changed for packaging; those checks were not rerun.

Extracted working copy: `.cache/build/6cd03b64cc2d6616/` under Genesis. Run its `verify-package.py` with the project Python for an offline hash check. The README gives local Docker commands and the optional future Google Cloud Build route. JSON schema, Docker image building and user-managed build identities are documented in [Google's configuration reference](https://docs.cloud.google.com/build/docs/build-config-file-schema), [image-building guide](https://docs.cloud.google.com/build/docs/building/build-containers) and [service-account guide](https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts), reviewed 17 October.

Offline integrity, corruption refusal, archive CRCs, privacy selection and repeated byte-identical packaging passed. The cloud template deliberately contains an unconfigured build identity. Cloud Build was not in the earlier local-build route; its coverage, source staging/storage, identity/IAM and bounded cost need review before any remote submission. No build, push, trigger, API enablement, IAM change, deployment or live model call was performed. Local image build/start remains blocked by the missing Docker/Podman engine; that acceptance gate is unchanged.
# Updated local candidate — not submitted

`genesis-build-candidate-ab0ff27cddfc5918.zip` contains tested source `ab0ff27cddfc5918495c8d7ba87f54ab90fcf666259e4d3a86f74001958aab2a`, including removal of the special local 12-attempt ceiling. SHA256: `8c163047411481a14276e34e4dd8472d79523f557a56511a241a38b882ee1929`. Package integrity and Cloud Build SDK schema passed. Local checks: 82 unit tests, 12 fresh emulator integration tests, production build and genuine A5 result display. No new cloud build/image/update is claimed. The currently deployed private source remains `efd33c4f...`. Human candidate freeze, held-out comparison and full funded cloud AI testing remain pending.



Latest local candidate (18 October 2026): `genesis-build-candidate-e8d4de34cecf4f82.zip`, SHA-256 `18b87bb22ad449a889ae46d06cca7717d07b5ad7d2feed1a8eab11b25e0d1edb`. Source fingerprint `e8d4de34cecf4f8236ab4507298453f70425796ce7678cfcb258c8a4385decbf`. Includes the identity/review/A0/Evolution policy workflow, verified by 91 unit passes, 13 isolated integration passes, production build and browser journeys. Genuine revised triage, frozen human feedback and A5 insufficient-evidence result are verified locally. Package integrity and Cloud Build configuration schema passed; images are not built and this candidate has not been submitted or deployed. New cloud execution authorization is required. Current deployed services remain on the earlier efd33 source.
