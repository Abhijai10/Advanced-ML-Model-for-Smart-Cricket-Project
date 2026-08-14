# Supabase Staging Verification

Use `scripts/verify_supabase_staging.py` after a staging Supabase project is configured. The script uses generated marker data only and never uploads real cricket footage.

## Required Variables

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_PUBLISHABLE_KEY`

Optional but needed for deeper checks:

- `SMART_CRICKET_STAGING_TEST_USER_A_ID`
- `SMART_CRICKET_STAGING_TEST_USER_A_TOKEN`
- `SMART_CRICKET_STAGING_TEST_USER_B_ID`
- `SMART_CRICKET_STAGING_TEST_USER_B_TOKEN`
- `SMART_CRICKET_EVIDENCE_SUPABASE_BUCKET`

Keep service-role credentials backend-only. The script does not print secret values.

## Commands

Dry run:

```bash
python scripts/verify_supabase_staging.py --dry-run
```

Live verification:

```bash
python scripts/verify_supabase_staging.py
```

Machine-readable output:

```bash
python scripts/verify_supabase_staging.py --json
```

## What It Checks

- REST and Storage API connectivity
- Required table reachability: `profiles`, `analysis_sessions`, `shot_timeline_events`, `analysis_feedback`, `product_feedback`
- Trusted backend analysis insert/read/cleanup when a test user ID exists
- User isolation when two test-user access tokens exist
- Browser write denial for trusted analysis history
- Analysis feedback insert
- Product feedback insert
- Evidence bucket upload/sign/delete when the bucket is configured
- Cleanup of every created marked record/object

All records and objects include `smart_cricket_staging_verification` plus a unique run ID.

## Interpreting Results

`PASS` means that check completed successfully.

`SKIPPED_EXTERNAL_CREDENTIAL` means the script could not run a credential-dependent check because the relevant live staging token, user ID, or bucket was not supplied.

`DRY_RUN` means no writes were performed.

`FAIL` means an executable check failed. The script exits non-zero if any check fails.

Supabase now may require explicit table exposure to the Data API for new projects. If schema checks fail with REST errors while migrations exist, inspect the Supabase Data API settings and table grants/RLS policies before changing application code.
