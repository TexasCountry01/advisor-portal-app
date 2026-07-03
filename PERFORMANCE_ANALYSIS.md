# Dashboard Performance Analysis
**Date:** July 3, 2026  
**Reported Issue:** Toggling between technicians, switching dashboard views, and navigating to the delegate management page takes 10–15 seconds  
**Environment:** Production — `reports.profeds.com`

---

## Affected Areas

1. **Technician / Admin dashboard** — toggling between "Me" and "Tiffany", switching "All Cases" / "My Cases"
2. **Member dashboard** — toggling between "My Cases", "Delegate", and "All Cases" views
3. **Delegate management page** — initial load and filtering

---

## Root Causes

### Problem 1 — No Pagination (Biggest Scaling Risk)
**File:** `cases/views.py` → `technician_dashboard()`, `admin_dashboard()`, `member_dashboard()`

All three dashboards pass the full `cases` queryset to the template with no `Paginator`. The template iterates `{% for case in cases %}` over every matching row. As cases accumulate daily, render time and query cost grow linearly with no upper bound.

```python
# Current — no page cap
context = {'cases': cases, ...}
```

---

### Problem 2 — 18 Separate COUNT Queries Per Tech/Admin Dashboard Load
**File:** `cases/views.py` → `_build_staff_quick_tiles()` + `stats` block

`_build_staff_quick_tiles()` issues **10 individual COUNT queries** against the case table. Immediately after, the `stats` block issues **8 more** — all against the same table with the same WHERE conditions. None of these results are shared or reused.

```
_build_staff_quick_tiles():
  queryset.filter(status='submitted').count()              ← query 1
  queryset.exclude(status__in=[...]).count()               ← query 2
  queryset.filter(status='completed', ...).count()         ← query 3
  queryset.filter(status='pending_review').count()         ← query 4
  queryset.filter(status='hold').count()                   ← query 5
  queryset.filter(Q(has_member_updates=True)|...).count()  ← query 6
  queryset.filter(date_due=today).exclude(...).count()     ← query 7
  queryset.filter(date_due=tomorrow).exclude(...).count()  ← query 8
  queryset.filter(date_due__gte=today, ...).count()        ← query 9
  queryset.filter(date_due__lt=today).exclude(...).count() ← query 10

stats block:
  cases.count()                                            ← query 11
  cases.filter(status='submitted').count()                 ← query 12
  cases.filter(status='accepted').count()                  ← query 13
  cases.filter(status='resubmitted').count()               ← query 14
  cases.filter(status='pending_review').count()            ← query 15
  cases.filter(status='accepted', review_status=...).count() ← query 16
  cases.filter(status='completed').count()                 ← query 17
  cases.filter(urgency='rush').count()                     ← query 18
```

**Total: 18 COUNT queries before a single case row is fetched.** Every tech toggle fires all 18 again.

---

### Problem 3 — N+1 Query Loops for Unread Counts
**File:** `cases/views.py` → `technician_dashboard()`, `member_dashboard()`

#### Technician dashboard — 1 query per case
```python
# Current — 1 query per case (150 cases = 150 queries)
for case in cases:
    unread_count = UnreadMessage.objects.filter(case=case, user=user).count()
    case.unread_message_count = unread_count
```

#### Member dashboard — 2 queries per case (worse)
The member dashboard fires **two** separate COUNT queries per case — one for chat messages, one for lifecycle notifications:
```python
# Current — 2 queries per case (100 cases = 200 queries)
for case in cases:
    chat_unread = UnreadMessage.objects.filter(case=case, user=user).count()
    lifecycle_unread = CaseNotification.objects.filter(
        case=case, member=case.member, is_read=False
    ).exclude(notification_type='member_update_received').count()
    case.unread_message_count = chat_unread + lifecycle_unread
```

The member dashboard also does `cases = list(cases)` to materialize all rows into memory, then re-sorts using Python's `sorted(..., key=lambda x: ...)` — bypassing SQL ORDER BY entirely and loading all ORM objects into memory unnecessarily.

---

### Problem 4 — Member Dashboard Rebuilds the Case Queryset from Scratch for Stats
**File:** `cases/views.py` → `member_dashboard()`

After fetching and filtering `cases`, the view creates an entirely new `all_cases` queryset with the same base filter — then fires 5 more COUNT queries for tile stats and 8 more for the stats block:

```python
# Re-queries the DB from scratch — does not reuse the already-filtered queryset
all_cases = Case.objects.filter(member_id__in=delegated_member_ids)
stats = {
    'total_cases': all_cases.count(),          # query N+1
    'submitted': all_cases.filter(...).count(), # query N+2
    ...                                         # 6 more
}
member_quick_tiles = _build_member_quick_tiles(all_cases, user)  # 5 more COUNTs
```

Also, `draft_cases` for the banner is a third separate query on the same filtered set.

---

### Problem 5 — Missing Database Indexes on Heavily Queried Fields
**File:** `cases/models.py` → `Case.Meta.indexes`

The existing indexes cover `(status, date_submitted)`, `(member, date_submitted)`, and `(assigned_to, status)`. The four due-date tile queries and the alerts tile hit columns with **no index**, forcing MySQL to do a full table scan on every dashboard load.

| Field | Used In | Indexed? |
|---|---|---|
| `date_due` | 4 tile queries (due_today, due_tomorrow, due_next_7d, past_due) | **No** |
| `has_member_updates` | alerts tile query | **No** |
| `(date_due, status)` | all due-date tiles filter by both | **No** |

---

### Problem 6 — Delegate Management Page: Triple-Query the Member Table
**File:** `accounts/views.py` → `delegate_management()`

Three separate issues on this page:

**6a. The full member table is queried twice with the identical query:**
```python
# Both queries are identical — only one is needed
all_members           = User.objects.filter(role='member', is_active=True).order_by(...)
all_possible_delegates = User.objects.filter(role='member', is_active=True).order_by(...)
```

**6b. `all_members.count()` fires a third query** after the queryset is already defined, then the template iterates `all_members` causing Django to fire a fourth fetch of the same rows:
```python
context = {
    'all_members': all_members,           # template iterates → SELECT * (query 3)
    'total_members': all_members.count(), # fires COUNT (query 4) — redundant
}
```

**6c. No limit on dropdown population** — As the member base grows, all active members are loaded into memory for two `<select>` dropdowns with no filtering or search. With 500 members this sends 500+ rows to the template twice.

---

## Query Count Summary

| Page / Action | Queries Fired |
|---|---|
| Tech dashboard load (no filter) | 18 COUNTs + N+1 per case + 3 review banner queries |
| Tech dashboard — toggle to Tiffany | Full reload: 18 COUNTs + N+1 per case |
| Member dashboard — toggle view | Full reload: 13 COUNTs + **2×N+1** per case + Python sort |
| Delegate management page | 4 queries against the member table (2 identical) |

---

## Options

### Option A — Quick Wins (Low Risk, ~1 hour)
Fixes Problems 3 and 5. Surgical changes with no UX impact.

**A1: Replace N+1 loops with single annotated queries**
```python
# Tech dashboard — 150+ queries → 1
from django.db.models import Count
unread_counts = {
    row['case_id']: row['cnt']
    for row in UnreadMessage.objects
        .filter(case__in=cases, user=user)
        .values('case_id').annotate(cnt=Count('id'))
}
for case in cases:
    case.unread_message_count = unread_counts.get(case.pk, 0)

# Member dashboard — 200+ queries → 2 (one per model)
chat_counts = {
    row['case_id']: row['cnt']
    for row in UnreadMessage.objects
        .filter(case__in=cases, user=user)
        .values('case_id').annotate(cnt=Count('id'))
}
lifecycle_counts = {
    row['case_id']: row['cnt']
    for row in CaseNotification.objects
        .filter(case__in=cases, member__in=[c.member for c in cases], is_read=False)
        .exclude(notification_type='member_update_received')
        .values('case_id').annotate(cnt=Count('id'))
}
for case in cases:
    case.unread_message_count = (
        chat_counts.get(case.pk, 0) + lifecycle_counts.get(case.pk, 0)
    )
```

**A2: Add missing indexes via migration**
```python
# In Case.Meta.indexes, add:
models.Index(fields=['date_due']),
models.Index(fields=['has_member_updates']),
models.Index(fields=['date_due', 'status']),
```

**A3: Fix delegate management page duplicate query**
```python
# Use a single queryset for both purposes
all_members = User.objects.filter(role='member', is_active=True).order_by(...)
# Pass the same queryset to both template vars; replace all_members.count() with len()
```

**Estimated improvement:** 3–8 seconds saved depending on case volume.

---

### Option B — Consolidate COUNTs into Single Aggregations (Medium, ~3–4 hours)
Fixes Problems 2 and 4. Replaces all individual `.count()` calls with a single `aggregate()` using `Case/When` conditional sums — one query per dashboard instead of 18.

```python
from django.db.models import Sum, Case, When, IntegerField

counts = queryset.aggregate(
    submitted   = Sum(Case(When(status='submitted', then=1), default=0, output_field=IntegerField())),
    on_hold     = Sum(Case(When(status='hold', then=1), default=0, output_field=IntegerField())),
    need_review = Sum(Case(When(status='pending_review', then=1), default=0, output_field=IntegerField())),
    scheduled   = Sum(Case(When(status='completed', actual_release_date__isnull=True,
                                scheduled_release_date__isnull=False, then=1), default=0, output_field=IntegerField())),
    due_today   = Sum(Case(When(date_due=today, then=1), default=0, output_field=IntegerField())),
    due_tomorrow= Sum(Case(When(date_due=tomorrow, then=1), default=0, output_field=IntegerField())),
    due_next_7d = Sum(Case(When(date_due__gte=today, date_due__lte=next_7d, then=1), default=0, output_field=IntegerField())),
    past_due    = Sum(Case(When(date_due__lt=today, then=1), default=0, output_field=IntegerField())),
    rush        = Sum(Case(When(urgency='rush', then=1), default=0, output_field=IntegerField())),
    completed   = Sum(Case(When(status='completed', then=1), default=0, output_field=IntegerField())),
)
```

The `stats` block becomes redundant and can be populated from the same `counts` dict.  
Also: replace `cases = list(cases)` + Python `sorted()` on the member dashboard with SQL `.order_by()` on the queryset before evaluation.

**18 queries → 1 query per dashboard.** Estimated improvement: 2–5 seconds.

---

### Option C — Add Pagination (Medium, ~2–3 hours)
Fixes Problem 1. Caps rows fetched, rows rendered, and N+1 iterations per page load.

```python
paginator = Paginator(cases, 50)
page_obj = paginator.get_page(request.GET.get('page'))
context['cases'] = page_obj
```

This is the most important **long-term fix** — without it, load times will grow indefinitely as cases accumulate. Pagination also reduces the N+1 impact from the full case count to at most 50 per page.

**Estimated improvement:** Render time becomes constant regardless of total case count.

---

### Option D — Async Tile Counts (Larger, ~1 day)
Separates tile COUNT queries from the initial page render entirely. The page loads immediately with the case list; tiles populate 1–2 seconds later via a lightweight AJAX call to a dedicated API endpoint. Makes perceived load time near-instant regardless of data volume, and is the best long-term UX approach.

This is additive with Options A–C.

---

## Recommendation

Implement **A + B + C** in sequence across all three affected areas.

| Fix | Problem | Queries Eliminated | Effort |
|---|---|---|---|
| A1: Replace N+1 loops (tech + member) | Problem 3 | ~150–200 queries per load | 45 min |
| A2: Add 3 indexes | Problem 5 | Full table scans on 4 queries | 15 min |
| A3: Fix delegate page duplicate query | Problem 6 | 2–3 redundant queries | 15 min |
| B: Consolidate COUNTs (tech + member) | Problems 2 & 4 | 30+ COUNT queries | 3–4 hrs |
| C: Paginate all dashboards | Problem 1 | Caps all future growth | 2–3 hrs |

**Cumulative expected result:** 10–15 second loads reduced to 1–3 seconds on current data volume, with flat performance as the dataset grows.

---

## Implementation — `feature/performance-optimizations`

**Branch:** `feature/performance-optimizations`  
**Commit:** `a936fd8`  
**Date:** July 3, 2026  
**Files changed:** `cases/views.py`, `cases/models.py`, `accounts/views.py`, `cases/migrations/0038_…`, `cases/templates/cases/technician_dashboard.html`, `cases/templates/cases/admin_dashboard.html`, `cases/templates/cases/member_dashboard.html`  
**Status:** Deployed to TEST (`test-reports.profeds.com`). Migrations applied. Gunicorn running healthy (1 master + 3 workers).

All five recommended options (A1, A2, A3, B, C) were implemented in this single commit. The sections below describe each change precisely.

---

### A1 — Replace N+1 Loops with Batch Queries

**Technician dashboard** (`technician_dashboard()`, ~line 730):

The per-case unread-message loop was replaced with a single annotated query executed against the current page's case IDs only (post-pagination — see C below):

```python
# Before: 1 query per case
for case in cases:
    unread_count = UnreadMessage.objects.filter(case=case, user=user).count()
    case.unread_message_count = unread_count

# After: 1 query for all cases on the current page
from django.db.models import Count as _Count
paginator = Paginator(cases, 50)
page_obj = paginator.get_page(request.GET.get('page', 1))
page_cases = list(page_obj.object_list)
_unread_map = {
    row['case_id']: row['cnt']
    for row in UnreadMessage.objects
        .filter(case_id__in=[c.pk for c in page_cases], user=user)
        .values('case_id').annotate(cnt=_Count('id'))
}
for case in page_cases:
    case.unread_message_count = _unread_map.get(case.pk, 0)
```

The same pattern was applied identically to `admin_dashboard()`.

**Member dashboard** (`member_dashboard()`, ~line 450):

The member dashboard had a worse N+1 — two queries per case (chat and lifecycle). Both were replaced with two batch queries operating on the current page only:

```python
# Before: 2 queries per case (N unread + N lifecycle = 2N total)
for case in cases:
    chat_unread = UnreadMessage.objects.filter(case=case, user=user).count()
    if case.member_id in notif_enabled_member_ids:
        lifecycle_unread = CaseNotification.objects.filter(
            case=case, member=case.member, is_read=False
        ).exclude(notification_type='member_update_received').count()
    else:
        lifecycle_unread = 0
    case.unread_message_count = chat_unread + lifecycle_unread

# After: 2 queries total for the entire page
_chat_map = {
    row['case_id']: row['cnt']
    for row in UnreadMessage.objects
        .filter(case_id__in=[c.pk for c in page_cases], user=user)
        .values('case_id').annotate(cnt=_Count('id'))
}
_lifecycle_map = {
    row['case_id']: row['cnt']
    for row in CaseNotification.objects
        .filter(
            case_id__in=[c.pk for c in page_cases],
            member_id__in=notif_enabled_member_ids,
        )
        .exclude(notification_type='member_update_received')
        .values('case_id').annotate(cnt=_Count('id'))
} if notif_enabled_member_ids else {}
for case in page_cases:
    case.unread_message_count = _chat_map.get(case.pk, 0) + _lifecycle_map.get(case.pk, 0)
```

The `_lifecycle_map` query is skipped entirely when `notif_enabled_member_ids` is empty (pure member with no delegate notifications).

**Net change:** N+1 eliminated across all three dashboards. With pagination capping pages at 50 cases, the worst case is now 2 queries for unread counts (technician/admin) or 3 queries (member: chat + lifecycle + optional skip) regardless of total case count.

---

### A2 — Add Missing Database Indexes

**File:** `cases/models.py` → `Case.Meta.indexes`  
**Migration:** `cases/migrations/0038_case_cases_case_date_du_50b226_idx_and_more.py`

Three indexes added:

```python
models.Index(fields=['date_due']),
models.Index(fields=['has_member_updates']),
models.Index(fields=['date_due', 'status']),
```

These target the fields used by the four due-date tile queries (`due_today`, `due_tomorrow`, `due_next_7d`, `past_due`) and the `alerts` tile (`has_member_updates`). Before this migration, all four due-date tile computations and the alerts tile caused full table scans on the `cases` table. The composite `(date_due, status)` index covers the most common filter pattern — all four due-date tiles exclude completed/cancelled/draft by status — allowing MySQL to satisfy the condition from the index alone without reading data rows.

The migration was generated by Django's `makemigrations` and applied cleanly to the TEST database (migration `0038` in the `cases` app dependency chain).

---

### A3 — Eliminate Duplicate Member Table Queries on Delegate Management Page

**File:** `accounts/views.py` → `delegate_management()` (~line 761)

Before: two identical `User.objects.filter(role='member', is_active=True)` querysets were created and handed to the template separately, causing Django to execute the same SELECT twice when the template iterated both variables. A third `all_members.count()` fired a COUNT query after the queryset was already defined.

```python
# Before: 3–4 queries against the users table
all_members = User.objects.filter(role='member', is_active=True).order_by(...)
all_possible_delegates = User.objects.filter(role='member', is_active=True).order_by(...)
context = {
    'all_members': all_members,            # template iteration → SELECT (query 3)
    'all_possible_delegates': all_possible_delegates,  # template iteration → SELECT (query 4)
    'total_members': all_members.count(),  # COUNT (query 5)
}

# After: 1 query total
all_members = list(User.objects.filter(role='member', is_active=True).order_by(...))
context = {
    'all_members': all_members,
    'all_possible_delegates': all_members,  # same list object, no second query
    'total_members': len(all_members),      # O(1) on already-materialized list
}
```

Wrapping in `list()` at assignment time materialises the queryset once. Both template dropdowns reference the same Python list object. `len()` on a list is O(1) with no database round-trip.

---

### B — Consolidate All COUNT Queries into Single Aggregations

This was the highest raw-query-count fix. Every dashboard's stats block and both tile-builder functions were rewritten to issue a single `aggregate()` call using conditional `Sum(Case(When(...)))` expressions.

#### `_build_staff_quick_tiles()` — 10 queries → 2

The 10 individual `.count()` calls were consolidated into one `aggregate()`. The `alerts` tile was left as a separate `.count()` because it requires an `Exists` subquery (checking `UnreadMessage` per case), which cannot be expressed as a simple conditional sum in the same aggregate:

```python
# Before: 10 queries
return {
    'submitted': queryset.filter(status='submitted').count(),
    'pending': queryset.exclude(status__in=['completed', 'cancelled', 'draft']).count(),
    'scheduled': queryset.filter(...).count(),
    ...
    'past_due': queryset.filter(date_due__lt=today).exclude(...).count(),
}

# After: 1 aggregate + 1 Exists-backed COUNT = 2 queries
inactive = Q(status__in=['completed', 'cancelled', 'draft'])
counts = queryset.aggregate(
    submitted=Sum(DbCase(When(status='submitted', then=1), default=0, output_field=IntegerField())),
    pending=Sum(DbCase(When(~inactive, then=1), default=0, output_field=IntegerField())),
    scheduled=Sum(DbCase(When(
        status='completed', actual_release_date__isnull=True,
        scheduled_release_date__isnull=False, then=1
    ), default=0, output_field=IntegerField())),
    need_review=Sum(DbCase(When(status='pending_review', then=1), default=0, output_field=IntegerField())),
    on_hold=Sum(DbCase(When(status='hold', then=1), default=0, output_field=IntegerField())),
    due_today=Sum(DbCase(When(Q(date_due=today) & ~inactive, then=1), default=0, output_field=IntegerField())),
    due_tomorrow=Sum(DbCase(When(Q(date_due=tomorrow) & ~inactive, then=1), default=0, output_field=IntegerField())),
    due_next_7d=Sum(DbCase(When(Q(date_due__gte=today, date_due__lte=next_7d) & ~inactive, then=1), default=0, output_field=IntegerField())),
    past_due=Sum(DbCase(When(Q(date_due__lt=today) & ~inactive, then=1), default=0, output_field=IntegerField())),
)
has_unread = Exists(UnreadMessage.objects.filter(case=OuterRef('pk'), user=user))
counts['alerts'] = queryset.filter(Q(has_member_updates=True) | has_unread).count()
return {k: (v or 0) for k, v in counts.items()}
```

The `{k: (v or 0)}` normalisation replaces any `None` result (which MySQL returns for `SUM` over an empty set) with `0`, preventing template rendering errors.

#### `_build_member_quick_tiles()` — 5 queries → 2

Same pattern. 4 of the 5 tile values moved into one aggregate; `alerts` stays separate because it uses two `Exists` subqueries:

```python
counts = queryset.aggregate(
    ready_14d=Sum(DbCase(When(status='completed', actual_release_date__isnull=False,
        actual_release_date__gte=ready_since, then=1), default=0, output_field=IntegerField())),
    pending=Sum(DbCase(When(
        ~Q(status__in=['cancelled', 'draft']) &
        ~Q(status='completed', actual_release_date__isnull=False), then=1
    ), default=0, output_field=IntegerField())),
    on_hold=Sum(DbCase(When(status='hold', then=1), default=0, output_field=IntegerField())),
    drafts=Sum(DbCase(When(status='draft', then=1), default=0, output_field=IntegerField())),
)
counts['alerts'] = queryset.filter(has_unread_msg | has_unread_notif).count()
return {k: (v or 0) for k, v in counts.items()}
```

#### Technician dashboard stats block — 8 queries → 1

```python
# Before: 8 separate COUNT queries
stats = {
    'total': cases.count(),
    'submitted': cases.filter(status='submitted').count(),
    'accepted': cases.filter(status='accepted').count(),
    ...
    'rush': cases.filter(urgency='rush').count(),
}

# After: 1 aggregate
_s = cases.aggregate(
    total=_Count('id'),
    submitted=Sum(DbCase(When(status='submitted', then=1), default=0, output_field=IntegerField())),
    accepted=Sum(DbCase(When(status='accepted', then=1), default=0, output_field=IntegerField())),
    resubmitted=Sum(DbCase(When(status='resubmitted', then=1), default=0, output_field=IntegerField())),
    pending_review=Sum(DbCase(When(status='pending_review', then=1), default=0, output_field=IntegerField())),
    needs_revision=Sum(DbCase(When(status='accepted', review_status='revisions_requested', then=1), default=0, output_field=IntegerField())),
    completed=Sum(DbCase(When(status='completed', then=1), default=0, output_field=IntegerField())),
    rush=Sum(DbCase(When(urgency='rush', then=1), default=0, output_field=IntegerField())),
)
stats = {k: (v or 0) for k, v in _s.items()}
```

#### Admin dashboard stats block — 10 queries → 1

Same structure. The admin dashboard has two additional stats (`unassigned`, `total_members`, `total_technicians`) — the latter two come from separate session/user queries and are added to the dict after the aggregate:

```python
_s = all_cases.aggregate(
    total=_Count('id'),
    submitted=Sum(DbCase(When(status='submitted', then=1), ...)),
    accepted=Sum(DbCase(When(status='accepted', then=1), ...)),
    resubmitted=Sum(DbCase(When(status='resubmitted', then=1), ...)),
    hold=Sum(DbCase(When(status='hold', then=1), ...)),
    pending_review=Sum(DbCase(When(status='pending_review', then=1), ...)),
    completed=Sum(DbCase(When(status='completed', then=1), ...)),
    rush=Sum(DbCase(When(urgency='rush', then=1), ...)),
    unassigned=Sum(DbCase(When(assigned_to__isnull=True, then=1), ...)),
)
stats = {k: (v or 0) for k, v in _s.items()}
stats['total_members'] = active_members        # from session query (unchanged)
stats['total_technicians'] = active_technicians
stats['requiring_review'] = stats['pending_review']   # alias, no extra query
```

#### Member dashboard stats block — 8 queries → 1

```python
_s = all_cases.aggregate(
    total_cases=_Count('id'),
    draft=Sum(DbCase(When(status='draft', then=1), ...)),
    submitted=Sum(DbCase(When(status='submitted', then=1), ...)),
    accepted=Sum(DbCase(When(
        Q(status='accepted') | Q(status='completed', actual_release_date__isnull=True), then=1
    ), ...)),
    resubmitted=Sum(DbCase(When(status='resubmitted', then=1), ...)),
    completed=Sum(DbCase(When(status='completed', actual_release_date__isnull=False, then=1), ...)),
    cancelled=Sum(DbCase(When(status='cancelled', then=1), ...)),
    rush=Sum(DbCase(When(urgency='rush', then=1), ...)),
)
stats = {k: (v or 0) for k, v in _s.items()}
```

**Aggregate summary for option B:**

| Location | Before | After |
|---|---|---|
| `_build_staff_quick_tiles()` | 10 queries | 2 (aggregate + 1 Exists COUNT) |
| `_build_member_quick_tiles()` | 5 queries | 2 (aggregate + 1 Exists COUNT) |
| Technician dashboard stats | 8 queries | 1 aggregate |
| Admin dashboard stats | 10 queries | 1 aggregate |
| Member dashboard stats | 8 queries | 1 aggregate |
| **Total** | **41 queries** | **7 queries** |

---

### B (supplemental) — Member Dashboard Python Sort Replaced with SQL ORDER BY

**File:** `cases/views.py` → `member_dashboard()`

The member dashboard previously materialised all case rows into a Python list with `cases = list(cases)` and then applied a 28-branch `if/elif` chain using `sorted(..., key=lambda x: ...)` to sort in application memory. This bypassed the database sort entirely, forced all ORM objects into memory, and handled `None` values in nullable date fields with arbitrary fallbacks (`timezone.now()`).

This was replaced with SQL `ORDER BY` applied to the queryset before pagination, using a lookup dict:

```python
from django.db.models import F as _F

_sql_sorts = {
    'external_case_id': 'external_case_id',   '-external_case_id': '-external_case_id',
    'workshop_code':    'workshop_code',       '-workshop_code':    '-workshop_code',
    'employee_first_name': 'employee_first_name', '-employee_first_name': '-employee_first_name',
    'date_submitted':   'date_submitted',      '-date_submitted':   '-date_submitted',
    'status':           'status',              '-status':           '-status',
    'urgency':          'urgency',             '-urgency':          '-urgency',
}
_null_sorts = {
    'date_due':         _F('date_due').asc(nulls_last=True),
    '-date_due':        _F('date_due').desc(nulls_last=True),
    'date_accepted':    _F('date_accepted').asc(nulls_last=True),
    '-date_accepted':   _F('date_accepted').desc(nulls_last=True),
    'date_completed':   _F('date_completed').asc(nulls_last=True),
    '-date_completed':  _F('date_completed').desc(nulls_last=True),
}
if sort_by in _sql_sorts:
    cases = cases.order_by(_sql_sorts[sort_by])
elif sort_by in _null_sorts:
    cases = cases.order_by(_null_sorts[sort_by])
```

Nullable date fields (`date_due`, `date_accepted`, `date_completed`) use `F('field').asc(nulls_last=True)` / `.desc(nulls_last=True)`, which emits `ORDER BY field ASC NULLS LAST` in the SQL. This is semantically correct (nulls sort last rather than being replaced with an arbitrary `timezone.now()` fallback). Non-nullable string and datetime fields use a plain string key for `order_by()`.

The `list(cases)` materialisation was removed entirely; the queryset stays lazy until pagination evaluates it in the next step.

---

### C — Pagination (50 Cases Per Page)

**Files:** `cases/views.py` (all three dashboards), three dashboard templates

All three dashboard views now paginate the case queryset before evaluating it:

```python
paginator = Paginator(cases, 50)
page_obj = paginator.get_page(request.GET.get('page', 1))
page_cases = list(page_obj.object_list)   # only used for batch unread annotation
context = {
    'cases': page_obj,
    'page_obj': page_obj,
    ...
}
```

`page_obj` (a `Page` instance) is passed as `cases` in the context so that existing `{% for case in cases %}` template loops continue to work without modification. The `page_obj` key is passed alongside for access to pagination metadata.

The N+1 batch queries (A1) operate on `page_cases` — the materialised list of the current page — so they fetch unread counts for at most 50 cases regardless of total case volume.

**Template pagination controls** were added to all three templates. The controls only render when there is more than one page, and include previous/next links, a sliding window of page numbers (±3 from current), and a count line:

```html
{% if page_obj.paginator.num_pages > 1 %}
<nav aria-label="Case pagination" class="mt-3">
  <ul class="pagination pagination-sm justify-content-center">
    {% if page_obj.has_previous %}
      <li class="page-item">
        <a class="page-link" href="?...&page={{ page_obj.previous_page_number }}">Previous</a>
      </li>
    {% else %}
      <li class="page-item disabled"><span class="page-link">Previous</span></li>
    {% endif %}

    {% for page_num in page_obj.paginator.page_range %}
      {% if page_num >= page_obj.number|add:"-3" and page_num <= page_obj.number|add:"3" %}
        <li class="page-item {% if page_num == page_obj.number %}active{% endif %}">
          <a class="page-link" href="?...&page={{ page_num }}">{{ page_num }}</a>
        </li>
      {% endif %}
    {% endfor %}

    {% if page_obj.has_next %}
      <li class="page-item">
        <a class="page-link" href="?...&page={{ page_obj.next_page_number }}">Next</a>
      </li>
    {% else %}
      <li class="page-item disabled"><span class="page-link">Next</span></li>
    {% endif %}
  </ul>
  <p class="text-center text-muted small mt-1">
    Showing {{ page_obj.start_index }}–{{ page_obj.end_index }} of {{ page_obj.paginator.count }} cases
  </p>
</nav>
{% endif %}
```

Pagination links preserve all existing filter/sort query parameters by using `filter_params` from the view context (already built by `build_filter_params(request)`).

---

## Post-Implementation Query Count Summary

| Page / Action | Before | After |
|---|---|---|
| Tech dashboard — full load | 18 COUNTs + N per page + 3 banner | 9 + 1 unread batch + 3 banner |
| Tech dashboard — toggle to Tiffany | 18 COUNTs + N per page | 9 + 1 unread batch |
| Member dashboard — toggle view | 13 COUNTs + 2N per page + Python sort | 5 + 2 unread batches + SQL sort |
| Admin dashboard — full load | 18 COUNTs + N per page | 9 + 1 unread batch |
| Delegate management page | 4–5 queries (2 identical SELECTs + COUNT) | 1 SELECT |

N = number of cases on page. With pagination, N ≤ 50 always.

---

## Migrations Included in This Commit

| Migration | App | Description |
|---|---|---|
| `0038_case_cases_case_date_du_50b226_idx_and_more` | `cases` | Adds `date_due`, `has_member_updates`, and `(date_due, status)` indexes |
| `0024_alter_auditlog_action_type` | `core` | Adds `case_accessed` choice to `AuditLog.ACTION_CHOICES` (from prior commit `e8a4a60`) |

Both migrations were applied to the TEST server database on July 3, 2026.

---

## Known Remaining Issues

- **Manager dashboard** not reviewed or updated — likely has the same N+1 unread loop and separate COUNT queries as the technician dashboard.
- **Option D (async tile counts)** not implemented — tile counts are still computed synchronously on every page load. This remains the best long-term UX improvement for perceived load time.
- **No `pip install` step in deploy scripts** — if new packages are added to `requirements.txt`, the deploy scripts will not install them automatically.
