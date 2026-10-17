# Credit verification — pending

17 October authorization update: the user explicitly requested foundation resource creation while funding details are worked out. Foundation creation proceeded under that instruction; see [actual resources and verification](deployment-recovery.md#provisioned-foundation--17-october-2026). This is authorization to provision, not evidence of credits, an agreed spending cap or permission to claim funding verified. Live model execution remains disabled.

17 October read-only check: the Cloud Billing API confirms `genesis-aicb` has billing enabled and a linked account. This establishes the existing link only; account approval, available credits, expiry, eligible services and quotas remain unverified. The masked account ID and sanitized response are retained only in ignored local evidence/internal planning. No access token, full account ID or response payload was printed or saved. Google documents the [Cloud Billing API as free of charge](https://cloud.google.com/billing/v1/pricing); [ProjectBillingInfo](https://docs.cloud.google.com/billing/docs/reference/rest/v1/ProjectBillingInfo) reports the link/open-account state, not promotional credit coverage. No services, billing configuration, deployments or model calls were changed/enabled by this check.

Interim update (16 October): the user confirmed Gemini Developer API Free Tier and available shared Secret Manager allowance. Existing secret `testing_free_gemini_api`, version 1, passed one payload-suppressed CLI access check. This verifies the interim key-storage connection only; the cloud funding and deployment checks below remain pending.

Updated 16 October 2026 (Australia/Sydney). Project target: `genesis-aicb` / `638299117256`. Neither the project ID nor an environment flag proves funding coverage. Local work G01–G14 is implemented; live work remains gated.

## Where to find the details

1. Open [Billing for genesis-aicb](https://console.cloud.google.com/billing?project=genesis-aicb) while signed into the approved Google account.
2. Open the project's linked billing account. Record its display name or masked ID; confirm it is the account approved for this project.
3. Open Credits (or the promotional-credit details from Billing Overview). Copy the credit name/status, remaining value and currency, Scope, and End date. Google documents those fields in its [billing troubleshooting guide](https://docs.cloud.google.com/billing/docs/how-to/resolve-issues).
4. Check the credit terms/Scope for Gemini through Vertex AI, Cloud Run, Firestore, Cloud Tasks, Cloud Build and Artifact Registry, including exclusions. Record anything unknown rather than assuming coverage. Do not upgrade billing to perform this check.

Share only these non-secret facts:

| Required evidence | Current value |
| --- | --- |
| Approved linked billing account (name or masked ID) | Unknown |
| Credit name and available status | Unknown |
| Remaining value and currency | Unknown |
| Expiry, including timezone when available | Unknown |
| Eligible services / Scope and exclusions | Unknown |
| Quotas and current project access | Not verified |
| Cloud operator/admin Firebase UIDs | Not supplied |

Credentials, passwords, access tokens, private keys and payment details must not be shared or committed. If billing details are inaccessible, the billing account administrator must provide the credit facts; the application cannot infer them.

## After evidence is supplied

Verify account linkage, credit applicability/expiry, service quotas, ADC identity, current official model/location availability and rate-card terms before any bounded smoke test or provisioning. Record an explicit verification expiry in deployment configuration (`CREDIT_VERIFIED_UNTIL`); the admin API cannot extend it.

Live cloud AI additionally requires cloud mode, `LIVE_AI_ENABLED=true`, `CREDITS_VERIFIED=true`, unexpired verification, matching `VERIFIED_CLOUD_MODEL_ID`/`GEMINI_MODEL`, an explicit `VERIFIED_CLOUD_LOCATION`, today's admin-enabled control, a worker lease and an available attempt slot. New UTC days start disabled. The cloud SDK branch is prepared but not executed; the separate opt-in local Developer API path has only the recorded connectivity check. Task dispatch has its own disabled gate; setting flags does not establish funding, model support, deployed identity or live investigation evidence.

The later real-feedback and explicit candidate-freeze checkpoints still require operator actions. Repository/submission destinations, rights/eligibility and the official cutoff remain external release inputs.
