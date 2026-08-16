# Technician Dashboard Default: Option 2 Analysis

## Objective

Align the benefits technician dashboard with the team’s operational goal: “What do I work on next?”

## Current state from code

The technician dashboard is controlled by two separate defaults:

1. The assignment scope (`assigned`): `mine` or `all`
2. The quick queue filter (`quick_filter`): `submitted`, `pending`, `alerts`, etc.

The app already supports the right architecture for the desired behavior. The issue was that the default startup state was still effectively broad and not action-oriented.

Key findings in the codebase:

- [cases/views.py](cases/views.py) loads the saved technician preference and defaults to `all` when no preference exists.
- The dashboard quick tiles already include the relevant queue states, including `Need to Accept`, `Pending Completion`, `On Hold`, `Need Review`, and `Active Alerts`.
- The default sort behavior already resolves to `date_due` when no sort is saved, which is the right operational ordering for a “work next” queue.
- The system keeps `Need to Accept` and `Active Alerts` as separate tile views, rather than folding them into the default queue, which is consistent with the recommended product flow.

## Recommended product approach

### Option 2: Default to My Cases + Pending Completion

This is the recommended default for technicians.

Behavior:

- Default assignment scope: `My Cases`
- Default quick filter: `Pending Completion`
- Default ordering: `Date Due` ascending/most urgent first
- Keep `Need to Accept` and `Active Alerts` available as separate tile views

Why this fits the requirement:

- It surfaces the technician’s immediate queue first.
- It avoids the noise of the global queue or broad “all cases” view.
- It respects the existing quick-filter architecture instead of introducing a new special-case dashboard.
- It leaves escalation and review queues available without making them the startup default.

## Why not make the default “all cases” or “alerts”?

- `all` makes the dashboard feel like a broad operational monitor rather than a personal work queue.
- `alerts` is useful for triage but not the core “what is next?” default.
- `Need to Accept` is the intake queue, not the ongoing work queue for assigned technicians.

## Local implementation applied

The local dashboard behavior was adjusted to default technicians to:

- assigned scope = `mine`
- quick filter = `pending`
- sort = `date_due` if the user has not explicitly chosen a different sort

This keeps the default aligned with the “my work next” behavior while preserving the existing tile-based navigation for other queues.

## Notes on the supporting workflow

The separate operational issues we reviewed showed that:

- the hold workflow is a formal, system-managed workflow that uses structured case state changes
- the manual chat flow is a separate user communication path
- terminal statuses like declined/cancelled are intentionally unassigned after workflow completion
- unread alert rows are user-scoped and not automatically cleared just because a case becomes unassigned

Those behaviors are separate from the dashboard default and are not the core cause of the default queue design problem.
