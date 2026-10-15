# Genesis workspace

- Keep all application source, package manifests, environments, configuration and build output in this directory. Run project commands with Genesis as the working directory.
- The parent context directory contains design references, not application code. Do not publish the original internal documents.
- Use the project-local Firebase CLI through npm scripts; do not upgrade the unrelated global Firebase installation.
- Use the demo-aml-insight project ID for local emulators. Bind emulator services to 127.0.0.1. Do not substitute a real project for an emulator test.
- Free tooling and verified free allowances/credits only. Do not activate paid billing, buy subscriptions, create paid services or run live AI requests without verifying the approved account and credit coverage.
- Never commit credentials, local environments, generated logs or emulator exports.
- Follow the six-role architecture and recommendation-only scope in ../context/ai-builder-cup-architecture.html. Candidate prompts, skills and scoring changes must not activate themselves.
- Keep source records, model outputs, operator feedback and synthetic reference labels separate. Do not fake live AI results.
- An MCP server configured below is a development integration, not one of the application's six workflow roles.

