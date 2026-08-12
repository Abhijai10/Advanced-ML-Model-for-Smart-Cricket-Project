# Production Readiness Audit History

## PR #2

PR #2, `production-hardening` into `main`, contains the earlier production-hardening base. It fixed the most severe upload-analysis bug, improved validation, separated health and readiness, and introduced the first polished frontend pass. It remains a draft integration PR.

## PR #3

PR #3, `production-readiness-execution` into `production-hardening`, is the active closure PR. It adds feedback governance, evidence lifecycle handling, JWT/JWKS coverage, rate-limit adapters, CI/container checks, frontend productization, and ML evaluation governance.

## DeepSeek Audit Findings

Valid findings included:

- filename-based inference;
- weak upload validation;
- forged trusted history;
- incomplete auth/JWKS validation;
- in-memory-only rate limiting;
- public audio lifecycle;
- camera cleanup;
- missing real-video E2E;
- Docker hardening;
- missing frontend/browser CI.

Partial or externally blocked findings included:

- production Supabase verification;
- natural TTS provider;
- true process-isolated inference timeout;
- larger player-disjoint dataset;
- coach validation.

Invalid or overstated findings were treated carefully: the project did not mark an item fixed unless the code and tests proved the relevant behavior.

## Lessons

The project’s hardest bugs were trust bugs, not syntax bugs. The fix pattern was consistent:

```text
make the boundary explicit
→ make the state truthful
→ add a regression test
→ document the limitation
```

## Final Release Position

The project is strongest as a restricted internal beta candidate after PR #3 is green. Public production remains blocked by external evidence and deployment gates.
