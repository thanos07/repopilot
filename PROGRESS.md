# Implementation checklist

- [x] Source audit and approved architecture
- [x] Separate RepoPilot codebase
- [x] Cobalt workspace and responsive navigation
- [x] Django models and migrations
- [x] Session authentication, CSRF and ownership
- [x] Public repository validation and bounded snapshot loading
- [x] Search/read context tools and exact-text patch tool
- [x] Bounded model loop and failure feedback
- [x] Provider usage and conservative cost reservation
- [x] Disposable network-disabled E2B adapter
- [x] Saved patch checkpoints and explicit retry
- [x] Final-verification and digest-bound approval gate
- [x] GitHub App publisher with draft-only PRs
- [x] Local backend unit/integration tests
- [x] Ten synthetic fixture cases and live evaluation command
- [x] Frontend production build
- [x] Docker, Render blueprint, CI and setup documentation
- [x] Live DeepSeek request with actual credentials
- [x] Custom E2B template built; sandbox smoke test and live task verification passed.
- [ ] Independently confirm sandbox cleanup after successful and failed runs.
- [x] Local PostgreSQL migration completed; Redis and Celery supported the live publishing workflow.
- [ ] Validate PostgreSQL, Redis, and Celery in a hosted deployment.
- [x] Live GitHub App branch/PR integration
- [ ] Live agent evaluation results and baseline comparisons
- [ ] Full backend deployment activation
- [ ] Browser interaction/accessibility QA and WebMCP runtime validation

The static product preview and synthetic examples are explicitly separate from live execution.

## Student budget update - 2026-09-11

- [x] New-task API estimate cap lowered to $0.05; 12 turns, 24 tools, four verification attempts.
- [x] Cumulative per-account recorded API allowance defaults to $4.00, checked before model calls; response limit 2,048 tokens.
- [x] Final verification slot reserved; UI displays actual task limit and recorded estimate.
- [x] 32 backend tests passed, including cross-task allowance, retry accounting and final verification reservation; frontend production build passed.
- [x] Migration and local upgrade/recruiter explanation included in README.
- [x] First successful demo task recorded approximately $0.00215 in estimated model usage; sandbox charges excluded.

## First live workflow completed - 2026-09-11

- Built the custom E2B Python/pytest template and passed a sandbox smoke test.
- Demo task reported 6 passing tests, compared with 2 passing and 2 failing before the fix.
- Migrated local SQLite data to PostgreSQL; imported 56 records and confirmed the approved task, two patches, and one approval.
- Authenticated the GitHub App with installation access restricted to mdtnoor/repopilot-demo.
- Published the approved patch as draft PR #1:
  https://github.com/mdtnoor/repopilot-demo/pull/1
- Reviewed the published diff: quantity multiplication plus two regression tests; existing assertions preserved.
- PR remains a draft and has not been merged. Test evidence comes from RepoPilot's sandbox; no GitHub checks were recorded.
- This is one successful demo, not a measured reliability benchmark. Production deployment and broader evaluations remain pending.
