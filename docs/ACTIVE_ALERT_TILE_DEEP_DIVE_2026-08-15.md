# Active Alert Tile Deep Dive
Date: 2026-08-15
Scope: Investigation only; no code changes made.

## Executive summary
The reported issue is not a deployment or data-loss problem. It is a semantic mismatch between the business expectation of "active alerts" and the actual logic used to populate the Active Alerts tile.

The current staff dashboard logic does not count every case that has activity or visible alert signals. It counts only cases that satisfy a narrow rule:

- the case is not a draft
- the case has an unread-message record for the relevant assigned technician or scoped tech user
- the tile definition does not count row-level "New Info" flags or other non-unread-message signals

This is explicitly codified in [cases/views.py](../cases/views.py#L143-L191) and [cases/views.py](../cases/views.py#L225-L268). The code comments are direct evidence of the intended behavior:

- "Drafts excluded; count only unread-message driven alerts."
- "Keep 'New Info' (has_member_updates) as a row badge signal, but do not let it inflate the red Active Alerts tile/filter."

That means the current version of the app is behaving as designed under the current implementation, even if the business expectation is broader than the code.

## Question being resolved
The business question is essentially:

- Are we counting every case with active alert-like updates?
- Or are we counting only cases with unread message rows assigned to the relevant staff user?

The code shows the second interpretation is the one currently implemented.

## Evidence from the code

### 1) Staff quick filter logic for the Alerts tile
In [cases/views.py](../cases/views.py#L143-L191), the `quick_filter == 'alerts'` branch does the following:

1. `alert_qs = queryset.exclude(status='draft')`
   - Drafts are removed from the alert universe.

2. For technician users:
   - If a specific tech is scoped, it checks whether there is an unread message for that user on the case.
   - Otherwise it checks whether there is an unread message for the case's assigned technician.

3. For non-technician staff, it also checks unread messages for the assigned technician.

The filter is therefore built from `UnreadMessage.objects.filter(case=OuterRef('pk'), user=...)`.

### 2) Staff quick tile counts for the Alerts tile
In [cases/views.py](../cases/views.py#L225-L268), the `counts['alerts']` value is set using the same unread-message existence check.

This is the exact logic behind the tile count:

- count cases with unread messages for the assigned tech
- exclude drafts
- do not count `has_member_updates` as a tile contribution

### 3) Model definition confirms unread rows are the source of truth
The model in [cases/models.py](../cases/models.py#L1237-L1285) defines `UnreadMessage` as a table that tracks unread status per message/user/case:

- `message` foreign key
- `user` foreign key
- `case` foreign key
- `unique_together = [['message', 'user']]`

The model comment says:

- "Track which users have read which messages."
- "When a message is read by a user, the record is deleted."

This tells us the system treats unread status as a derived, ephemeral record keyed to message + user, not as a general-purpose case alert state model.

## Why the tile appears too low
The user is reporting that there are many cases with lot of alerts that are not visually reflected in the Active Alerts tile.

This is exactly what would happen under the current rules when the cases have one or more alert-like signals that are not represented as unread-message rows for the assigned tech.

Examples:

- case has a member update or a row-level "New Info" indicator
- case has activity that is visible in the row but not encoded as an assigned-tech unread record
- case is a non-draft but does not qualify under the unread-message rule
- the case has multiple staff recipients and the tile is keyed to a single assigned-tech unread row rather than a broader alert state

The code explicitly says the row signal is retained while the red tile count remains narrow.

## Why the current design is so strict
The system is intentionally not treating the dashboard tile as a catch-all for all case activity. It is effectively a workflow urgency signal, not a complete audit of case chatter.

This is supported by multiple comments and guardrails in [cases/views.py](../cases/views.py#L149-L166) and [cases/views.py](../cases/views.py#L230-L240):

- alerts are active-case only
- unread-message driven
- not inflated by row badges or member update indicators

This is a deliberate policy decision to keep the top tile meaningful and focused on true unread work items.

## Why the user experience feels wrong
From a user perspective, the confusion is understandable:

- they see visible case activity or row indicators
- they expect those to count toward an alert bucket
- but the tile excludes them for a specific definition

The issue is not that the tile is mathematically broken. The issue is that the screen is mixing two different concepts:

1. row-level signal: "there is something to look at on this case"
2. tile count: "this case qualifies under the unread-message-based active alert rule"

Those are not the same thing.

## The unread logic is the real source of truth
The system uses `UnreadMessage` rows as the source of truth for alert eligibility. That is the most important fact from this analysis.

From [cases/views.py](../cases/views.py#L5576-L5638):

- staff unread counts are built by filtering `UnreadMessage` rows for the assigned tech
- member unread counts are built from the viewer's own unread rows
- when a user marks messages as read, rows are deleted for the case/viewer context

So the tile is not counting a persistent case-level alert flag. It is counting a transient unread-message condition.

## The probable root cause of the report
The most likely root cause is not a failed calculation. It is a mismatch between business expectation and implementation policy:

- The business expects "alert counts should reflect visible active case activity".
- The implementation expects "alert counts should reflect unread-message records for the relevant staff user."

Because the system is not maintaining a separate, broader case alert state field, the user is effectively being shown the strict unread-message definition rather than the broader activity definition.

## What the analysis supports
This investigation supports the following conclusion:

- The current alert tile behavior is internally consistent with the code.
- The behavior is intentionally narrower than a general "any alert-like activity" count.
- The issue is a rules mismatch, not a failed deployment or a broken query.

## Practical interpretation
If the business intends the active tile to represent all real-time case issues, then the current tile logic is too restrictive.

If the business intends the active tile to represent only unread-message-driven action items, then the current tile behavior is likely correct and the user expectation needs to be aligned to the product definition.

## Recommendation
No code change is required for this investigation. The next step should be a business decision on the definition of an "Active Alert":

Option A: Keep the current unread-message-only definition
- Best if the tile is meant to be a focused action queue
- Accepts that some activity will not appear in the tile

Option B: Broaden the definition to include non-message alert-like activity
- Best if the tile is meant to reflect all active case signal
- Requires a richer alert state model than `UnreadMessage` alone

Option C: Separate the concepts visually
- Keep a narrow Active Alerts tile
- Show row-level or supplemental indicators for other signal types
- Reduces confusion without changing backend semantics

## Final conclusion
The deeper investigation shows that the alert tile is not counting "all alerts on cases"; it is counting cases that satisfy the unread-message-driven staff alert rule. That rule is explicit in the code and is enforced by the `UnreadMessage` model and the dashboard filter logic.

The user complaint is therefore valid as a product-definition complaint, but it is not evidence of a broken implementation under the current rules.

The real issue is that the business definition of an alert has not been kept aligned with the code's definition of an alert.
