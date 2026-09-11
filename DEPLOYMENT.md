# Deployment and activation

## Frontend

Deploy `frontend/` to Vercel as a Next.js project. Build with `npm run build`, output `out`. Configure `NEXT_PUBLIC_API_URL=https://api.YOUR_DOMAIN/api` at build time to enable the backend UI. Rebuild when that value changes. With no value, the frontend is the read-only illustrative preview.

Host the app and API on same-site custom subdomains (for example `app.example.com` and `api.example.com`) for the session-cookie design. Unrelated `vercel.app` and `onrender.com` domains can be blocked by browser cross-site cookie policies. Do not work around this by storing refresh tokens in localStorage. Alternatively add a reviewed same-origin API proxy in a non-static frontend deployment.

## Django and worker

Use `infra/render.yaml` as a starting blueprint. It provisions definitions for the API and worker, not the database, Redis, or sandbox. It has not been deployed or cost-validated in a live account.

Configure on both API and worker:

- `DJANGO_DEBUG=false`, a strong shared `DJANGO_SECRET_KEY`.
- `DATABASE_URL` for managed PostgreSQL with TLS; a direct/session connection is required for publication advisory locks, not a transaction-mode pooler.
- `REDIS_URL` for a private or TLS-enabled durable Redis broker.
- Exact `DJANGO_ALLOWED_HOSTS`, and `FRONTEND_ORIGINS` matching the frontend origin.
- The model and E2B settings from `backend/.env.example`.
- `LIVE_EXECUTION_ENABLED=true` only after the first configured sandbox smoke check.

Before serving traffic, run `python manage.py migrate` once from the backend environment, then `python manage.py createsuperuser`. No default password or demo administrator is seeded. Start the API and a concurrency-one worker. `/health/` reports API process health; it is not a database/queue readiness guarantee.

The API container never receives a Docker socket and never executes cloned repository code. The E2B adapter creates a network-disabled sandbox for each test attempt using your prebuilt template. Template CPU/RAM sizing and sandbox quotas must be checked in your E2B account before enabling arbitrary supported repository submissions.

## First live verification checklist

1. Sign in, add a small public Python repository you control, and create a focused draft.
2. Start it and confirm API response returns promptly while the worker continues.
3. Close/reopen the browser; confirm persisted progress appears.
4. Confirm baseline errors are distinguished from failures and passing tests.
5. Confirm actual token metadata appears; compare the estimate with provider billing.
6. Confirm every E2B instance is killed or expires, including after a failed run.
7. Test cancellation and iteration limits with the same repository.
8. Configure the GitHub App on this repository, then enable publishing.
9. Approve the final patch, create a draft PR, and verify its diff equals the approved change.
10. Confirm retry does not create a second PR or overwrite an unrelated branch.

These checks require your external accounts and have not been performed by the local test suite. Do not treat the illustrative preview as proof of integration.

## Costs

Budget separately for API hosting, the always-on worker, Redis, PostgreSQL, model calls and sandbox seconds. E2B credits are one-time usage credits, not unlimited free operation. Model estimates use configurable ceiling rates; they intentionally do not claim invoice precision. No paid infrastructure was provisioned as part of this source delivery.

## Operations

Run `python manage.py recover_stale_runs` after interrupted coding runs exceed 20 minutes without a heartbeat. Retry failed tasks explicitly. For a publishing crash, inspect the saved publication record and GitHub branch/PR before moving the task back to APPROVED through a reviewed operator repair. Keep a database backup; do not edit approved patches directly.

Current deployment gates: run the PostgreSQL CI job, test the E2B template, test live DeepSeek tool calls, and test GitHub publication before opening live execution to others.
