# Security policy

## Supported version

Security fixes target the current main branch.

## Reporting a vulnerability

Use GitHub's private "Report a vulnerability" option under the repository's Security tab when available.

If private reporting is unavailable, open an issue requesting a private contact channel without including vulnerability details, exploit code, credentials, or personal data.

Please do not disclose sensitive details in public issues or pull requests.

## Current scope

The public website is a read-only preview. Public registration and public task execution are planned for a future update.

Live execution and GitHub publishing are restricted to the private workspace operator. Publishing requires human approval and passing verification for the selected patch.

## Limitations

Passing tests and dependency scans do not guarantee the absence of vulnerabilities. Secret redaction is best effort. Sandbox cleanup during forced process termination and cross-process concurrency require further validation.

The static frontend CSP permits inline scripts and styles for Next.js hydration and theme initialization.

See [security configuration](docs/security-configuration.md) for deployment settings and remaining verification work.
