# Genesis release gates

## Single approved Cloud Build and push completed - 17 October 2026

The user explicitly allowed one build/image push within the verified **AUD 6 monthly alerts-only budget**, then requested resources be declared and verified before pushing. This supersedes the previous no-spend restriction **for this one build operation only**; it does not verify promotional/model credits or authorize live AI/deployment. The earlier setup command rejection was followed by the user's renewed go-ahead. Exactly one build was submitted and completed successfully; no additional build allowance is inferred.

Build ID: `fbca029c-cde5-41a3-9eba-99dee9b03e54`, Sydney, E2_STANDARD_2, 1200-second timeout, 118.60 seconds actual execution. All four steps succeeded, including source hashes, both image builds and network-isolated non-root health/static/signed-out denial smoke checks before push. Artifact Registry digests were independently read back: web `sha256:9723ec4321f4596b91fa4a13e7849aac94198829e1567844e5593c58daa8457f`; worker `sha256:2b52821c35989a47849a58430e3a23b4822b51c85c3532d7fe5ed42645c31658`. Image repository remains `australia-southeast1-docker.pkg.dev/genesis-aicb/genesis-demo-images`.

New verified build resources: Cloud Build API; `genesis-demo-build@genesis-aicb.iam.gserviceaccount.com` with project log writer, repository-scoped image writer and staging-bucket-scoped object viewer; managed Cloud Build agent role; private Sydney Standard staging bucket `genesis-aicb-build-source-638299117256-syd`, uniform access/public access prevention enforced, one-day source-object lifecycle and no soft delete. Source/runtime bytes match fingerprint `6cd03b64cc2d6616ee4ba4465c301453520c5a4bf572ff7b63e49549ccbaf426`; previous 70-unit/11-integration evidence is unchanged.

Readback shows **zero Cloud Run services** in Sydney and the existing queue **PAUSED**. No deployment, source-data publication, operator creation, model/secret access or model credit/live flags were enabled. Image vulnerability assessment remains unrun. List-rate compute estimate USD0.01186 before allowances excludes storage/registry/logging/network; actual billed cost and remaining monthly budget are unknown. Full handoff is in Genesis/docs/deployment-recovery.md; private proofs `.cache/build/build-push-verification.json` and `.cache/deploy/built-images.json`. G27 progresses; Cloud Run/runtime/Auth/model/genuine/user/release gates remain unfinished.

## Latest foundation update — 17 October 2026

The user explicitly authorized creating resources while funding is worked out, superseding the prior funding-first/M1-first order for foundation creation. Provisioned in `genesis-aicb`, Sydney: default Standard/Native Firestore with deletion protection, exact repository deny-all rules, 13 READY composite indexes and 14 field exemptions; `genesis-demo-images` Docker repository; `genesis-demo-triage` queue verified PAUSED; separate web/worker/tasks identities and scoped IAM; Firebase and web app `1:638299117256:web:6f36170a6efba49d5cb7fd`. Anonymous Firestore read returns 403. [Actual resource record](../Genesis/docs/deployment-recovery.md); sanitized evidence: `Genesis/.cache/deploy/foundation-verification.json`.

Funding remains unverified, not a blocker retroactively reinstated on this authorized foundation step. No live AI, cloud data publication, image upload, Cloud Run deployment or operator user creation occurred. Container execution, reviewed cloud publisher, Auth configuration/real users, verified model tuple and genuine workflow/release evidence remain unfinished. Earlier preparation-only observations below are historical, not the current resource inventory. G15–G30 are not marked fully complete by this partial foundation work.

Checked 17 October 2026, Australia/Sydney. Internal planning only; this file is excluded from the source archive and public repository.

## Verified local work

Latest code-completion batch, 17 October 2026: **CODE01-CODE04 implemented and locally verified; 70 unit tests passed and all 11 fresh-emulator integration tests passed with zero integration skips.** Production typecheck/build and full local Chromium journeys passed. The unit run's 11 emulator-only skips were executed separately. Source fingerprint: `6cd03b64cc2d6616ee4ba4465c301453520c5a4bf572ff7b63e49549ccbaf426`. Matching exact-JUnit unit receipt and sanitized evaluation record are captured. The publisher, immutable rate-card estimates, source-bound genuine-reference capture and safe export/link closure are ready for their later approved cloud integration. Details: [local integration handoff](../Genesis/docs/local-integration-handoff.md). No live request, secret access, cloud operation or publication was performed in this code batch; separate foundation records in deployment-recovery were preserved.

Current local review archive: `Genesis/.cache/release/genesis-source-089d4d4d3fe5dc7d.zip`, SHA256 `089d4d4d3fe5dc7d0f831a66598b6d5b1b111b30460887c97dc2778726834540`. Copy: `Genesis/submission/github-repository/genesis-source-draft-089d4d4d3fe5dc7d.zip`, with companion `.zip.sha256`. Its 108 source files plus manifest pass CRCs, every file hash and archive-link checks; repeat export is byte-identical. PREPARATION_ONLY, release_ready/publication_authorized false. Earlier copies remain preserved.

CODE05 image build/start remains blocked by absent Docker/Podman and no installed WSL distribution. CODE06 native checks pass; the complete M1 handoff still needs actual image execution. Genuine investigation, human grounding/review, A5, explicit candidate freeze, comparison, applicable cloud pricing/funding and deployment/final artifact evidence remain separate unfinished gates.

Historical baseline before this code-completion batch follows.

G01–G14 remain complete. Later tasks have implementation preparation but are not complete solely from local fixtures. Latest reports: 43 unit tests passed; all nine real Auth/Firestore emulator integration tests passed with zero integration skips. The nine emulator-only skips in the default unit command were executed separately. Code fingerprint: `f493f307a9a457f327125040b6a97adc5ed7be20ca7188a3f2cd77f1b1d3449a`. Typecheck/build, full Chromium journeys, strict Premium and design-token checks passed. Disabled cloud SDK transport and configuration-driven cloud sign-in are code-prepared; provider faults/auth responses were intercepted locally and do not verify real cloud execution.

Confirmed send failures preserve the active queued batch/children. Signed local HTTP delivery exercises the actual worker subprocess and rejects signed-out/tampered identities. Stale/duplicate deliveries do not repeat work. These are local identity fixtures, not verified Google IAM delivery.

## Funding and execution

Read-only Cloud Billing GET confirmed billing enabled for `genesis-aicb`, linked account ending **8F40F9**. The probe retains only a masked account identifier/status in `Genesis/.cache/cloud-billing-link-check.json`; its returned token was not written to application/evidence files or displayed. The CLI retains its normal private credential store. [Cloud Billing API pricing](https://cloud.google.com/billing/v1/pricing) states API use is free; [ProjectBillingInfo](https://docs.cloud.google.com/billing/docs/reference/rest/v1/ProjectBillingInfo) describes link/open-account status, without credit balance or promotional scope.

User response: billing has just been linked; no credit evidence is supplied for now. Do not infer a zero balance or available promotional funding. Account approval, credit name/value/currency, expiry, eligible services/exclusions and quotas remain unverified. ADC/runtime/task identities and actual cloud model/location/rate-card validation remain pending. Deployment/live/task switches remain disabled. No new secret access, model request, service enablement, billing change, resource provisioning or publication occurred.

## Deadline and participant evidence

The [official timeline](https://aibuildercup.com/) lists **18 October 2026** for prototype submission without an exact hour/timezone. The user explicitly confirmed the dashboard cutoff as **18 October 2026, 11:59 PM India Standard Time (UTC+05:30)**. Recorded timestamp: `2026-10-18T23:59:00+05:30`; UTC: `2026-10-18T18:29:00Z`; Sydney: **19 October 2026, 5:29 AM AEDT (UTC+11:00)**. Conversion was checked with the Windows Sydney timezone rules. The exact clock time is user-reported dashboard evidence, not an independently inspected authenticated portal. No further cutoff clarification is pending; this does not verify eligibility or authorize submission.

The [official FAQ](https://aibuildercup.com/Faqs.html) requires a registered team of two to four eligible participants, rather than solo entry. Participants must be professionals/entrepreneurs/startups, at least 21 and based in JAPAC; student participation is excluded. Actual registration, finalized roster and individual eligibility have not been confirmed. The public timeline puts registration/team formation before the current date; no roster change or organizer message was attempted.

The [published terms](https://docs.google.com/document/d/e/2PACX-1vRm7ChZ6Ij9fG7uFDkxzUMpwgVeBmnQ6cMDnAIEEX84AiLBOOQ9cYbl3S5OzFBbcVb8TF55s-eVpiXb/pub) require new implementation/assets made during the event, with Google Cloud as the main platform. They restrict third-party/confidential material and contain IP/licensing provisions for participant review. The separate copyright language about derivative applications is not recorded as organizer approval to enter earlier work. Permission/ownership of the historical AML ideas/materials and organizer reuse clarification remain unverified. No original internal materials are packaged and no license is granted by the export tool.

The [official submission requirements](https://aibuildercup.com/themes.html) call for Google AI integration, Google Cloud deployment, English materials and a PDF presentation. The FAQ/terms also require a working hosted demo, public GitHub source and a demonstration video shorter than 180 seconds. No artifact is claimed submitted or eligible solely because the local code runs.

## Local draft artifact

The user's five-item submission reminder is now tracked in [Genesis submission checklist](../Genesis/submission/README.md): prescribed-template pitch deck, working demo video, live prototype throughout evaluation, accessible GitHub repository and brief solution description. Each has its own folder/checklist with draft assets or explicit pending final values. The PDF/HTML, script and source archive are preserved review copies; a factual description draft is added. The prescribed template is still missing. These preparations do not satisfy final deliverable acceptance or authorize publication/deployment.

Archive: `Genesis/.cache/release/genesis-source-04a798c518eaa744.zip`.

SHA256: `04a798c518eaa744624ce661883d649833e6cccda48780f74a8df01b963a8a9c`.

Verified 88 allowlisted source files plus one manifest; archive CRCs and every file checksum pass. Repeated export produced identical bytes. Internal context, local agent configuration, environments, caches, logs, built assets and emulator evidence are excluded. The manifest is PREPARATION_ONLY, publication_authorized false and release_ready false. Source remains an uncommitted tested worktree, not a release revision. Earlier archives remain preserved. An eight-page offline PDF draft is at `Genesis/.cache/release/genesis-deck-draft-20261017.pdf`; source is `Genesis/docs/submission-draft.html`, with a 150-second draft script at `Genesis/docs/demo-script.md`. These are review drafts, not final submission or recorded-video evidence.

## Remaining gates

Operational setup is documented in [the step-by-step HTML resource guide](../Genesis/submission/deployed-prototype/resource-setup-guide.html), alongside the deployed-prototype checklist. Proposed names, role/configuration dependencies and separate funding/publication/live gates are explicit. The separate cloud source/configuration publisher is now implemented and locally checked; its actual apply still requires reviewed funding/source/identity approval. The existing seeder remains emulator-only. The guide itself does not create resources, clear funding or count as deployed verification.

- Local image execution: no Docker/Podman command found; read-only WSL enumeration returned no installed distribution. No engine was installed or cloud build attempted.
- Genuine evidence: approved bounded investigation, manual grounding, your analyst feedback, real A5, your explicit candidate freeze and stored held-out comparison.
- Release: verified funding/model/runtime identities; actual builds/deployment/revision IDs and signed-out journeys; final deck/video; approved repository/submission destinations and confirmed eligibility/cutoff.

G15–G30 remain unchecked until their own acceptance evidence exists. The source archive makes G29 partial; it does not complete submission preparation. Billing-only and the now-complete user-reported dashboard cutoff are recorded above. Credit coverage and other release inputs remain pending; no dependent live action proceeds from missing evidence.
