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
