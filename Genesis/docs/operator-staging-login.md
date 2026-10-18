# Stored operator login: private staging only

Local code is implemented; cloud setup and deployed acceptance are pending. The shortcut is off by default. Google and individually entered email/password sign-in remain available independently.

`OPERATOR_DEMO_LOGIN` is server-only JSON with exactly three nonempty strings: email, password and uid. Local mode rejects this configuration. `OPERATOR_DEMO_LOGIN_ENABLED` defaults to false and must remain false outside explicitly verified private staging. Never place the JSON in source, an image, a browser configuration, a URL or a log. Its dataclass representation excludes the secret.

When enabled on private staging, `/api/config` exposes only the stored email. `POST /api/operator/demo-login` accepts no credentials from the browser, requires the configured UID in both operator/admin allowlists, exchanges the stored password through Identity Toolkit and verifies the returned token identity. It returns only `idToken`, with no-store caching. The browser still validates the session and holds the token only in memory. Disabled, absent or local configurations return 404. This route intentionally relies on the private Cloud Run IAM boundary rather than an existing Firebase session.

## Pending cloud acceptance

- [ ] Obtain the separate authorization for secret/IAM/service changes and applicable spending coverage.
- [ ] Verify an existing Firebase user whose UID is already in both allowlists and whose password provider is enabled. Do not silently create a user, enable a provider or alter the allowlists.
- [ ] Verify the web service requires Cloud Run IAM authentication: no public/all-authenticated invoker grant, no disabled invoker IAM check and no public proxy bypass.
- [ ] Create `operator-demo-login` with the reviewed credentials; choose the approved storage/replication location. Do not copy the credential JSON into this runbook.
- [ ] Grant secret-level accessor permission only to the existing web runtime service account. Do not mount the secret on the worker.
- [ ] Mount the reviewed secret version into `OPERATOR_DEMO_LOGIN` and explicitly enable the staging-only flag.
- [ ] Verify stored, manually entered and Google sign-in; check actual UID/admin status, denied identities, timeout recovery and password absence from responses/logs.
- [ ] Record the actual secret version and private service revision without recording credentials.
- [ ] Before public release, disable the flag and remove the secret mount; verify demo-login returns 404 and stored email is absent from configuration. Only then consider changing web-service IAM.

No cloud change is performed by these instructions or by local tests. Public release must never retain this unauthenticated app-level admin-token shortcut.
