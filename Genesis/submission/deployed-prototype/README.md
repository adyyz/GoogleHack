# Live deployed prototype

Required: a deployed prototype link that remains available throughout evaluation. Status: not deployed. Billing linkage alone does not verify funded coverage or authorize execution.

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

Web/private-worker revision IDs: **Pending**.

Evaluation availability window and health-check responsibility: **Pending**.

Access/recovery evidence: image smoke checks passed; deployed journeys pending. Build `fbca029c-cde5-41a3-9eba-99dee9b03e54`, [actual resource/image handoff](../../docs/deployment-recovery.md).

## Local build package - 17 October 2026

Package: `genesis-build-package-89f5c10f20997a67.zip`, companion `genesis-build-package-89f5c10f20997a67.zip.sha256`. SHA256: `89f5c10f20997a67553de76a8700e18cb84a3ae420b0764fae16b4686253c79a`.

The bundle contains 40 exact runtime/build-context files from the verified source, plus a README, manifest, offline verifier and Google Cloud Build JSON template. It excludes private context, environments, credentials, local evidence and submission binaries. Its fingerprint is `6cd03b64cc2d6616ee4ba4465c301453520c5a4bf572ff7b63e49549ccbaf426`, matching the 70 unit / 11 emulator integration passing record. App code and dependencies were not changed for packaging; those checks were not rerun.

Extracted working copy: `.cache/build/6cd03b64cc2d6616/` under Genesis. Run its `verify-package.py` with the project Python for an offline hash check. The README gives local Docker commands and the optional future Google Cloud Build route. JSON schema, Docker image building and user-managed build identities are documented in [Google's configuration reference](https://docs.cloud.google.com/build/docs/build-config-file-schema), [image-building guide](https://docs.cloud.google.com/build/docs/building/build-containers) and [service-account guide](https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts), reviewed 17 October.

Offline integrity, corruption refusal, archive CRCs, privacy selection and repeated byte-identical packaging passed. The cloud template deliberately contains an unconfigured build identity. Cloud Build was not in the earlier local-build route; its coverage, source staging/storage, identity/IAM and bounded cost need review before any remote submission. No build, push, trigger, API enablement, IAM change, deployment or live model call was performed. Local image build/start remains blocked by the missing Docker/Podman engine; that acceptance gate is unchanged.
