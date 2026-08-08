# Legacy Rush Data Fix Verification (PROD)

Generated: 2026-08-08
Environment: Production (104.248.126.74)
Command: fix_legacy_terminal_rush
Source allowlist: docs/LEGACY_RUSH_TERMINAL_CASES_PROD.md

## Verification Summary

- Targeted case count: 14
- Audit entries written for targeted list: 14
- Remaining cancelled/declined cases with urgency=rush: 0

## Per-Case Audit Entries

| Case Number | Audit Timestamp (UTC) | Actor | Action Type | Urgency Before | Urgency After |
|---|---|---|---|---|---|
| WS000-2026-04-0542 | 2026-08-08T17:19:22.129446+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-05-0491 | 2026-08-08T17:19:22.145982+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-05-0546 | 2026-08-08T17:19:22.162466+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-05-0550 | 2026-08-08T17:19:22.178880+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-05-0572 | 2026-08-08T17:19:22.194548+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-05-0601 | 2026-08-08T17:19:22.209209+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-06-0010 | 2026-08-08T17:19:22.225986+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-06-0096 | 2026-08-08T17:19:22.240657+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-06-0100 | 2026-08-08T17:19:22.256406+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-06-0104 | 2026-08-08T17:19:22.271408+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-06-0388 | 2026-08-08T17:19:22.287173+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-06-0389 | 2026-08-08T17:19:22.302115+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-06-0409 | 2026-08-08T17:19:22.316597+00:00 | admin | case_rush_downgraded | rush | normal |
| WS000-2026-07-0283 | 2026-08-08T17:19:22.332632+00:00 | admin | case_rush_downgraded | rush | normal |

## Admin Audit Log Lookup

To review these in the admin panel, filter Audit Logs by:
- Action Type: case_rush_downgraded
- User: admin
- Date: 2026-08-08

These entries were written by the production data-fix command and are attached to each case record.
