# AI Builder Cup 2026: BFSI context brief

Verified against official web pages: **15 October 2026 (Australia/Sydney)**.

## Source status

The supplied [YouTube recording, starting at 11:06](https://www.youtube.com/watch?v=mhDd6qSBMg4&t=666s) could not be retrieved through the available browser access. This document summarizes official website information, not the recording. No speaker statements, video quotations, or topic timestamps have been verified. The supplied starting point does not establish where BFSI is discussed.

## BFSI theme and organizer expectations

**BFSI: Intelligent Risk, Fraud & Financial Experiences** covers banking, financial services, insurance, and adjacent industries. Suggested directions include fraud/risk reduction, complex-process automation, better customer interactions, and personalized financial experiences. These are possible directions, not a requirement to implement every one.

The expected output is a functioning prototype. Google AI models such as Gemini/Gemma or the listed agentic platforms are required; the themes page specifies Cloud Run or Firebase deployment. Materials must be in English, with a proposal deck exported to PDF.

Source: [Official themes and requirements](https://aibuildercup.com/themes.html).

## Proposed project use case: AML alert triage and feedback-driven improvement

**Status:** A candidate use case derived from the repository's AML materials, added to support task planning. It is not an organizer-specified problem statement, a verified explanation from the recording, or confirmation of the team's final scope. The implementation has not been audited for this brief.

### Who uses it and what problem it solves

The primary user is a bank's anti-money-laundering (AML) analyst reviewing transaction-monitoring alerts. A secondary user is a monitoring lead reviewing recurring sources of unnecessary alerts and proposed rule changes.

An alert identifies potentially suspicious activity, but the analyst still needs customer context, transaction history, supporting evidence, and a defensible reason to escalate or dismiss it. Repeated benign patterns can consume review time. Analyst decisions also provide feedback that could help improve future monitoring.

**Proposed product:** An AI-assisted investigation workspace that assembles alert evidence, explains risk indicators, drafts an investigation summary, captures the analyst's decision, and uses accumulated feedback to recommend monitoring improvements for human review.

This maps to BFSI through risk investigation and complex-process automation. An AML alert or analyst label is not proof that money laundering occurred.

### Example journey — illustrative synthetic scenario

A transaction-monitoring rule flags several transfers from an account. The analyst opens the alert and sees the triggering rule, relevant transfers, customer profile, and account history. The system identifies unusual patterns and drafts an evidence-linked explanation. If context is missing, it explicitly requests further review.

The analyst examines the evidence, records a disposition and reasoning, and decides whether further investigation is needed. Later, the monitoring lead reviews feedback across multiple alerts. The system identifies a recurring benign pattern and proposes a narrowly defined rule adjustment. A historical replay shows both the alerts that adjustment would avoid and the suspicious examples it might miss. The lead reviews the proposal before any operational change.

### Inputs, workflow, and outputs

| Stage | Required capability | Observable result |
| --- | --- | --- |
| Prepare evidence | Load synthetic alerts, transactions, customer/account context, and triggering rules. | A reproducible dataset with stable evidence identifiers. |
| Triage | Combine deterministic calculations with Google AI reasoning over the available evidence. | Risk indicators, a proposed priority/action, an investigation summary, and references to supporting records. |
| Human review | Let the analyst inspect findings and record a decision, notes, or an override. | A persisted review record linked to the alert and the original AI output. |
| Feedback analysis | Aggregate reviewed outcomes by rule/pattern; use AI to explain findings and propose improvements. | A recommendation with its supporting sample, limitations, and rationale. |
| What-if evaluation | Replay a proposed change against labeled examples before approval. | Counts of alerts avoided and suspicious cases put at risk, with examples for inspection. |

### Minimum demo scope and task breakdown

These are proposed work packages, not a claim that the features are absent. Inspect existing implementation before creating tickets; reuse must also be assessed against the competition's fresh-project requirement.

1. **Dataset and baseline:** Prepare synthetic benign, suspicious, and incomplete-context examples. Define reference labels and baseline review/detection behavior separately from AI predictions.
2. **Evidence-backed triage:** Implement one complete alert-to-summary path using Google AI. Calculate numerical facts in code and ensure generated claims can be traced to input records.
3. **Analyst workflow:** Provide an alert queue, investigation detail, and saved review decision. Include missing-data and AI-failure states that leave the case available for human review.
4. **Feedback and recommendation:** Aggregate analyst feedback and produce one evidence-backed improvement proposal. Insufficient feedback should produce an explicit limitation rather than a confident tuning recommendation.
5. **What-if comparison:** Evaluate that proposal on labeled examples, displaying efficiency gains alongside suspicious cases lost. Keep operational rule changes subject to human approval.
6. **Deployment and submission:** Deploy the end-to-end path on the required Google stack and prepare the repository, deck, and short demo.

The first demonstrable milestone is **one alert reviewed end-to-end with a saved analyst decision**. The differentiating milestone is **feedback leading to a recommendation whose tradeoffs can be inspected**. Do not make multiple autonomous agents a prerequisite; they are an implementation choice.

### Success criteria and boundaries

- An analyst can follow the full workflow without manually joining data from separate files.
- Investigation claims reference evidence; absent context and unsupported conclusions are visible.
- Review decisions and overrides survive a reload and remain linked to the relevant alert.
- Numerical metrics are computed from data, not invented by the language model.
- The demo compares against a stated baseline and reports dataset size, label source, and limitations. No improvement percentage is assumed in advance.
- The prototype assists investigation; production transaction blocking, autonomous case closure, regulatory filings, and automatic rule deployment are outside this proposed minimum scope.

### Local source material and planning constraints

- [Evolution Agent pitch](Evolution_Agent_Pitch.txt) describes per-alert enrichment, risk assessment, categorization, investigation summaries, analyst feedback, and aggregate recalibration recommendations.
- [AML scenario guide](scenario_AML.html) provides existing scenario material to inspect when selecting demo examples.
- The pitch references a separate PwC hackathon and Claude/AWS Bedrock. It is background material, not evidence that this project meets AI Builder Cup eligibility or platform requirements. Establish development provenance before assuming existing work can be submitted; a cloud migration alone does not establish eligibility.
- Historical pitch statistics and performance claims are not adopted here as validated facts.

This section supports a product backlog. Implementation-ready tickets still require checking the code, selecting the final demo dataset, and agreeing on measurable acceptance thresholds; this document does not establish those details.

## Judging criteria

| Official criterion | Weight | Organizer emphasis, paraphrased |
| --- | ---: | --- |
| Technical Merit & Gen AI Implementation | 40% | Useful GenAI, technical execution, scalability, and sustainability. |
| Problem Alignment & Impact | 25% | Fit to the selected challenge and value to stakeholders. |
| Innovation & Creativity | 25% | Differentiation and inventive GenAI application. |
| User Experience & Solution Design | 10% | Accessible usability and coherent integration. |
| **Total** | **100%** | |

Sources: [Official rubric](https://aibuildercup.com/themes.html), [FAQ confirmation that the same rubric applies across themes](https://aibuildercup.com/Faqs.html).

### Practical BFSI evidence — interpretation, not additional rules

| Criterion | Evidence our prototype could demonstrate |
| --- | --- |
| Technical / GenAI | Trace a real input through AI analysis, grounded evidence, and an analyst action. Explain what the model contributes; show a failure case and recovery. |
| Alignment / impact | Identify the financial-services user and workflow bottleneck. Measure review time, false positives, or another relevant outcome against a baseline. |
| Innovation | Compare the approach with an existing manual or rules-based workflow and demonstrate the specific improvement. |
| UX / design | Show a complete investigation journey with understandable findings, evidence links, and a clear next action. |

For an AML triage project, the proposed connection is risk investigation and process automation. This is our interpretation of theme fit; the sources do not mandate AML, autonomous agents, a particular architecture, or a particular model.

## Mandatory submission checklist

The [official FAQ](https://aibuildercup.com/Faqs.html) requires:

- [ ] A working deployed prototype URL.
- [ ] A demo video **under three minutes**.
- [ ] A public GitHub repository.
- [ ] A deck explaining the solution.
- [ ] A fresh project developed within the hackathon period.
- [ ] Google Cloud as the primary platform.
- [ ] One solution under one theme per team.

Additional preparation from the [themes page](https://aibuildercup.com/themes.html):

- [ ] English submission materials and a PDF deck.
- [ ] Required Google AI/platform integration and deployment.
- [ ] An accessible video link: YouTube, Vimeo, or public Google Drive.

## Competition overview

Hack2skill operates the competition with Google Cloud sponsorship. The website lists a USD 30,000 prize pool and a Singapore finale.

### Current published timeline

| Milestone | Published date, 2026 |
| --- | --- |
| Registration | 1 September–11 October |
| Team formation | 1 September–14 October |
| Prototype building and submission | 7 September–18 October |
| Prototype deadline | **18 October** |
| Evaluation | 19 October–6 November |
| Finalists announced | 7 November |
| Singapore Grand Finale | 4 December |

Source: [Official overview and timeline](https://aibuildercup.com/). Deadline time and timezone are not specified in the reviewed timeline; do not assume Sydney midnight.

### Eligibility and finale

Participants must be 21+, based in JAPAC, and working professionals, entrepreneurs, or startups. Students are excluded. Teams require 2–4 members; solo registration is permitted, solo participation is not. Cross-country JAPAC teams are allowed; multiple-team participation is prohibited.

Evaluation precedes shortlisting. Only two members per finalist team may attend, including at their own expense. Sponsored arrangements cover flights, accommodation, and finale-day meals; participants handle visas. Participation is free.

Source: [Official FAQ](https://aibuildercup.com/Faqs.html).

## Conflicting wording and unresolved details

- **Category mismatch:** The themes page's submission section names healthcare/education/social-good categories that conflict with its six industry themes. Treat this as unresolved wording, not a reason to relabel BFSI.
- **Deployment wording:** The themes page names Cloud Run/Firebase, while its submission section and FAQ also use broader GCP wording. Cloud Run or Firebase is the conservative preparation choice; confirm any alternative with the organizer.
- **Video duration:** The themes page says three minutes; the FAQ says under three minutes. Prepare a shorter video.
- **Dates:** Earlier secondary listings encountered during research gave 4 October; this brief uses the current official timeline above. The recording and linked terms have not been checked for conflicting dates or precedence.
- **Unverified recording:** BFSI examples, Q&A, slide details, verbal expectations, and any recording-specific changes remain unknown.
- **Other unknowns:** Reviewed pages do not establish an exact submission cutoff time, finale pitch duration, or a named judging panel. Consult the registered-team dashboard and organizer for current instructions.

These discrepancies are visible in the [themes page](https://aibuildercup.com/themes.html), [FAQ](https://aibuildercup.com/Faqs.html), and [overview](https://aibuildercup.com/). Organizer contact: **support+aibuildercup@hack2skill.com**. No organizer contact has been made for this brief.

## BFSI / AML preparation checklist — project guidance

The following are recommendations for our project, not organizer requirements:

- [ ] Define one analyst persona, one investigation problem, and one end-to-end demo journey.
- [ ] Use synthetic or appropriately de-identified sample data; keep secrets and customer data out of the public repository.
- [ ] Demonstrate how findings connect to transaction evidence and how an analyst reviews recommendations.
- [ ] Report measured results on a stated dataset and baseline. Distinguish observed improvement from projected business impact.
- [ ] When claiming fewer false positives, also measure missed suspicious cases or recall; avoid showing efficiency gains alone.
- [ ] Explain model limitations, uncertainty, auditability, and the role of human review. Avoid unsupported regulatory-compliance claims.
- [ ] Prepare the deployed demo, README/run instructions, architecture explanation, PDF deck, and a video shorter than three minutes.
- [ ] Check every submitted URL from a signed-out browser and verify that the deployed workflow works.
- [ ] Verify project creation dates against the fresh-project requirement and confirm deadline details in the team dashboard.

## Source index

1. [Supplied recording at 11:06 — content unverified](https://www.youtube.com/watch?v=mhDd6qSBMg4&t=666s).
2. [Official themes, requirements, and judging rubric](https://aibuildercup.com/themes.html).
3. [Official FAQ: submissions, eligibility, evaluation, and travel](https://aibuildercup.com/Faqs.html).
4. [Official overview and current timeline](https://aibuildercup.com/).

If a transcript becomes available, add a separate recording-notes section with verified timestamps and distinguish historical statements from current website requirements.
