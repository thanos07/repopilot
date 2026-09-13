# Security configuration and validation

## Deployment

The public Vercel deployment must remain a disconnected static preview. Never add model, GitHub, database or E2B credentials to the frontend. Local operator builds keep their API configuration.

Private production Django deployment requires:
- DJANGO_DEBUG=false
- DJANGO_SECRET_KEY: at least 50 characters, varied and randomly generated. Existing development or short keys fail startup; do not rotate a working key casually because it invalidates sessions.
- DATABASE_URL: PostgreSQL
- DJANGO_ALLOWED_HOSTS: explicit hosts, no wildcard
- FRONTEND_ORIGINS: exact HTTPS origins, without trailing paths or wildcards
- TRUST_PROXY_HTTPS=true only behind a proxy that strips client-supplied X-Forwarded-Proto and sets it correctly. Otherwise leave false. Misconfiguration can cause redirect loops; test HTTPS routing before enabling the backend.
- SECURE_HSTS_SECONDS: default 0. After HTTPS validation, start with a short period such as 300, then increase deliberately.
- SECURE_HSTS_INCLUDE_SUBDOMAINS=false and SECURE_HSTS_PRELOAD=false by default. Do not enable unless every affected domain is ready and the long-lived consequences are understood.

The frontend host controls its own HSTS. Inspect deployed responses before changing it. Django settings do not configure Vercel's static responses.

## CSP

frontend/vercel.json sets a production-only static-site CSP. External scripts, objects, frames and arbitrary connection origins are restricted. Inline scripts/styles remain allowed because the current static Next.js export uses inline hydration and theme initialization. No unsafe-eval is allowed. Do not copy this CSP unchanged to a separately hosted live operator frontend: its API origin would need an explicit connect-src allowance. Verify navigation, theme switching and preview tabs on the deployed site. A hash-based static CSP is future hardening.

## GitHub settings

Enable private vulnerability reporting in repository Settings → Security. SECURITY.md describes a conditional fallback until enabled. Enable Dependabot alerts/security updates if available. Review automated updates; do not auto-merge them. The CodeQL workflow uses advanced setup for Python and JavaScript/TypeScript; avoid enabling duplicate default setup. Its first actual result is available only after GitHub runs it.

Retain the existing CI checks. CodeQL has read-only source permission and security-events write for uploading results. No provider credentials are needed by any security workflow. Use branch protection/rulesets if available to require passing CI and review before merging.

## Remaining scope

No public signup, OAuth, billing, additional infrastructure or public execution is added. PostgreSQL locking and remote publication reconciliation remain unchanged; SQLite regression tests do not validate cross-process advisory locking. Runtime dependency audits must be rerun in the deployment's resolved environment because Python requirements include version ranges.
