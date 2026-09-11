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
- [ ] Live DeepSeek request with actual credentials
- [ ] Live E2B template and cleanup verification
- [ ] PostgreSQL/Redis/worker integration in deployment
- [ ] Live GitHub App branch/PR integration
- [ ] Live agent evaluation results and baseline comparisons
- [ ] Full backend deployment activation
- [ ] Browser interaction/accessibility QA and WebMCP runtime validation

The static product preview and synthetic examples are explicitly separate from live execution.

## Student budget update — 2026-09-11

- [x] New-task API estimate cap lowered to $0.05; 12 turns, 24 tools, four verification attempts.
- [x] Cumulative per-account recorded API allowance defaults to $4.00, checked before model calls; response limit 2,048 tokens.
- [x] Final verification slot reserved; UI displays actual task limit and recorded estimate.
- [x] 32 backend tests passed, including cross-task allowance, retry accounting and final verification reservation; frontend production build passed.
- [x] Migration and local upgrade/recruiter explanation included in README.
- [ ] Live API cost per successful task remains unmeasured.
