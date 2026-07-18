# Performance Scorecard — Data Immutability Technical Analysis

**Date:** 2026-07-18  
**Context:** The Performance Scorecard feeds formal HR technician evaluations. Numbers must not change after an admin has reviewed and approved a week. The current live-computation implementation is insufficient.

---

## Why Live Computation Is Insufficient

The scorecard currently runs 5 DB queries on each page load and computes all values in Python. For any week that has already closed, the following legitimate operations can retroactively change the numbers:

| Operation | Affected metrics |
|---|---|
| Admin changes `date_completed` on a past case | Reports Generated, On-Time Delivery, Report Accuracy, Cycle Time, Readiness Window |
| Admin changes `date_due` on a past case | On-Time Delivery, Readiness Window |
| Admin changes `date_submitted` on a case | Initial Submissions, ProFeds Errors, Cycle Time |
| L3 tech adds a review action (corrections/approval) after the week closes | L1/L2 Accuracy Rate, Submitted for Review |
| Admin toggles `has_profeds_error` on a past case | ProFeds Errors, Report Accuracy |

All of these operations are **legitimate business operations** in the L1/L2/L3 review workflow. This is not an edge case — it is expected behavior.

---

## Option 1 — Manual Admin Lock (Recommended)

### Data Model

```python
class ScorecardWeekSnapshot(models.Model):
    """Frozen weekly metric snapshot, created by an admin after reviewing the week."""

    week_start  = models.DateField(help_text='Monday of the week')
    week_end    = models.DateField(help_text='Sunday of the week')

    # NULL tech = team total row; non-null = individual tech row
    tech        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='scorecard_snapshots',
    )

    # Metric values
    reports_generated       = models.IntegerField(default=0)
    submitted_for_review    = models.IntegerField(default=0)
    initial_submissions     = models.IntegerField(default=0)
    l1l2_accuracy_pct       = models.FloatField(null=True, blank=True)
    on_time_pct             = models.FloatField(null=True, blank=True)
    profeds_errors          = models.IntegerField(default=0)
    report_accuracy_pct     = models.FloatField(null=True, blank=True)
    cycle_time_days         = models.IntegerField(null=True, blank=True)
    readiness_days          = models.IntegerField(null=True, blank=True)
    review_submitted        = models.IntegerField(default=0)

    # Audit fields
    locked_at   = models.DateTimeField(auto_now_add=True)
    locked_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='scorecard_locks',
    )
    lock_note   = models.CharField(max_length=255, blank=True)

    # Unlock audit
    unlocked_at = models.DateTimeField(null=True, blank=True)
    unlocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='scorecard_unlocks',
    )

    class Meta:
        unique_together = [('week_start', 'tech')]
        ordering = ['-week_start', 'tech__first_name']
```

### Files to Create / Modify

| File | Action | Purpose |
|---|---|---|
| `core/models.py` | Add | `ScorecardWeekSnapshot` model |
| `core/migrations/` | Generate | `makemigrations` |
| `core/views_reports.py` | Modify | `_build_scorecard_data()` reads snapshots for locked weeks |
| `core/views_reports.py` | Add | `scorecard_lock_week` view (POST) |
| `core/views_reports.py` | Add | `scorecard_unlock_week` view (POST, with confirmation) |
| `core/urls.py` | Add | Two new URL entries for lock/unlock |
| `templates/core/performance_scorecard.html` | Modify | Add 🔒/⚠️ indicators per week column; lock button UI |
| `core/admin.py` | Add | `ScorecardWeekSnapshot` registered in Django admin |

### Scorecard View Logic Change

```
For each of the 13 weeks:
    If a snapshot exists for this week → use snapshot values (show 🔒)
    Else → compute live (show ⚠️ Not yet locked)
```

### Lock Flow

1. Admin visits the scorecard, reviews a closed week's numbers
2. Clicks **"Lock Week Jul 6 – Jul 12"** button
3. System runs `_build_scorecard_data()` for that single week, writes one row per tech + one team-total row to `ScorecardWeekSnapshot`
4. Week column now shows 🔒 with locked values permanently
5. Admin name and timestamp recorded on every snapshot row

### Unlock Flow (emergency correction)

1. Admin clicks **"Unlock"** (requires a reason note)
2. All snapshot rows for that week are soft-deleted (or flagged as unlocked)
3. The unlock action is logged with who did it, when, and why
4. Week reverts to live computation
5. Admin can re-lock after corrections are verified

### Migration Path

- Existing scorecard continues working as-is during development
- Once the model is added, old weeks are all "unlocked" (live-computed) until an admin locks them
- No data migration needed — snapshots are populated on first lock

---

## Option 2 — Automated Weekly Snapshot (Cron)

### Cron Job

Runs every **Sunday at 11:59 PM** (or Monday at 12:01 AM):

```bash
# Add to crontab (see CRON_JOB_SETUP.md)
59 23 * * 0 /path/to/venv/bin/python /path/to/manage.py snapshot_scorecard_week
```

### Management Command

`core/management/commands/snapshot_scorecard_week.py` — calls `_build_scorecard_data()` for the week that just closed, writes to `ScorecardWeekSnapshot`. Skips if a snapshot already exists for that week.

### Risk

If the cron job fails silently (server restart, disk full, etc.), that week has no snapshot and remains live-computed indefinitely. Requires cron monitoring.

### Recommended addition

Even with a cron, add a manual "Lock" button as a fallback. This is Option 4 (Hybrid).

---

## Option 3 — Export as the Frozen Record

No new development. The timestamped PDF/CSV download is the immutable record. The PDF already captures:
- Generated date/time
- Generated by (admin name)

**Limitation:** No in-app frozen view. If numbers change between the export and a later review, the app shows different values than the HR tool received.

---

## Option 4 — Hybrid (Auto-snapshot + Admin Acknowledgment)

Combines Options 1 and 2:
- Cron auto-freezes each Sunday
- Admin must explicitly **acknowledge** (sign off) before the snapshot is considered "final for HR"
- Admin can re-lock with a documented reason if corrections are needed post-snapshot

This is the most rigorous but also the most complex. Suitable if the HR extraction is automated (rather than a manual admin CSV download).

---

## Recommendation

**Option 1 (Manual Admin Lock)** for the following reasons:

1. Corrections via the L1/L2/L3 workflow can happen after week close — admin needs to decide when corrections are "settled" before locking
2. The lock-then-export workflow naturally enforces a review step before HR data is submitted
3. The unlock audit trail provides accountability if a number ever needs to change
4. No cron dependency
5. Complexity is moderate and well-contained

**Implementation estimate:** 2–3 development sessions (model + migration + lock/unlock views + template changes).
