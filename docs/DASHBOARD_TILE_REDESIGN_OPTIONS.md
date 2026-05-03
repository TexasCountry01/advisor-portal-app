# Dashboard Tile Redesign — Options Analysis

**Date:** May 3, 2026  
**Context:** Adding 2 new tiles ("Due Next 7d" and "Overdue") to the Tech/Manager/Admin dashboard brings the total from 8 to 10 tiles. The current single flex-wrap row already pushes the boundary on 15" laptops. This analysis covers layout options to accommodate 10 tiles cleanly.

---

## Current Layout (8 tiles)

```
[ Tech Filter Row: All Cases | Ileana | Tiffany | Chris ]

[ Submitted ] [ Pending ] [ Need Review ] [ Scheduled ] [ On Hold ] [ Alerts ] [ Due Today ] [ Due Tomorrow ]
```
Two separate rows. At 1440px they fit; at 1280px (15" laptop at 100%) tiles begin to wrap.

---

## Options

### Option A — Intentional 2-Row Grid (user's "stacked" proposal)

Split tiles into two logical rows of 5:

```
[ Tech Filter Row: All Cases | Ileana | Tiffany | Chris ]

Row 1 — Workload:  [ Submitted ] [ Pending ] [ Need Review ] [ Scheduled ] [ On Hold ]
Row 2 — Urgency:   [ Alerts ] [ Due Today ] [ Due Tomorrow ] [ Due Next 7d ] [ Overdue ]
```

**Pro:** Clean visual grouping — "what's in the pipeline" vs. "what's urgent." Easy to read at any screen size. No font/size changes needed.  
**Con:** Pushes the queue table down by ~60–70px. On a 15" laptop at normal zoom, 2–3 fewer case rows are visible without scrolling.

---

### Option B — Single Horizontal Row, Compact Tiles (user's second mockup)

All 10 tiles in one row. Tiles narrower (~80–90px wide), two-line labels allowed.

```
[ Tech Filter Row ]

[ Need to Accept ] [ Pending ] [ On Hold ] [ Need Review ] [ Scheduled ] [ Due Next 7d ] [ Due Today ] [ Due Tomorrow ] [ Past Due ] [ Active Alerts ]
```

**Pro:** Queue table stays exactly where it is today — no vertical shift.  
**Con:** At 10 × ~90px = ~950px minimum width, tiles are tight on 15" laptops. Numbers must remain large enough to scan quickly. If a 4th tech name is added to the filter row, that row grows and wraps anyway.

---

### Option C — Merge Tech Filter Into the Tile Row *(recommended)*

Eliminate the separate tech-filter row entirely. Filters live on the **left**, tiles on the **right** of a single row.

```
[ All Cases | Ileana | Tiffany | Chris ]  ··  [ Submitted ] [ Pending ] [ Need Review ] [ Scheduled ] [ On Hold ] [ Alerts ] [ Due Today ] [ Due Tomorrow ] [ Due Next 7d ] [ Overdue ]
```

Net result: same vertical height as today (two separate rows become one combined row), even with 2 extra tiles. See mockup below.

**Pro:** Zero net change in vertical space vs. today. No stacking. Tiles and filters are visually co-located (they filter the same thing). Scales naturally as more tech names are added since the flex row wraps gracefully.  
**Con:** Row is visually "busier." If 5+ tech names are added, the combined row may wrap, but current 3–4 names is fine.

---

### Option D — Scrollable Single Row

Force all 10 tiles into one row with `overflow-x: auto` and a subtle scroll indicator.

**Pro:** Queue completely unaffected; tiles never wrap or stack.  
**Con:** Horizontal scrolling on a dashboard feels wrong. Easy to miss tiles off-screen edge. Not recommended.

---

### Option E — Two-Tier Collapsible

5 "workload" tiles always visible. 5 urgency tiles (Alerts, Due Today, Due Tomorrow, Due Next 7d, Overdue) collapse behind a small "Urgency ▾" toggle, saved to localStorage.

**Pro:** Full flexibility — techs who want the full picture expand it; those who don't, leave it collapsed. Zero vertical impact by default.  
**Con:** Adds a new interaction pattern. Techs might not discover the urgency tiles at first.

---

## Recommendation

**Option C now** — it costs zero vertical space versus today, requires no tile size changes, and naturally accommodates 10 tiles by sharing the existing tech-filter row. See mockup below.

**Option A** is the right call if readability and logical grouping (workload vs. urgency) matters more than the ~65px height trade-off. If the queue table shifts slightly lower, this is the cleanest solution long-term.

Option E is worth considering once the team has grown and personalization becomes valuable.

---

## Option C — HTML Mockup

See the mockup section below. The two changes from the current template are:

1. **Delete** the `<!-- Quick Tech Row -->` `<div class="row mb-3">` block entirely.
2. **Replace** the `<!-- Clickable Fast-Filter Tiles -->` row with a combined row that starts with the tech filter buttons on the left, followed by the tiles on the right.

```html
<!-- Combined Tech Filter + Fast-Filter Tiles (Option C) -->
<div class="row mb-3">
    <div class="col d-flex gap-2 align-items-center flex-wrap" style="justify-content: flex-end;">

        <!-- Tech filter buttons (left side) -->
        <small class="text-muted me-1">Pending:</small>
        <div class="btn-group me-3" role="group">
            <a href="?quick_tech=all&quick_filter={{ quick_filter }}"
               class="btn btn-sm btn-outline-primary quick-tech-btn {% if quick_tech == 'all' or not quick_tech %}active{% endif %}">
               All Cases
            </a>
            {% for tech in quick_technicians %}
            <a href="?quick_tech={{ tech.username }}&quick_filter={{ quick_filter }}"
               class="btn btn-sm btn-outline-primary quick-tech-btn {% if quick_tech == tech.username %}active{% endif %}">
               {{ tech.first_name }}
            </a>
            {% endfor %}
        </div>

        <!-- Divider -->
        <div style="width:1px; height:36px; background:#dee2e6; margin-right:8px;"></div>

        <!-- Stat tiles (right side) — 10 tiles -->
        <a class="tile-link {% if quick_filter == 'submitted' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=submitted">
            <div class="stat-mini bg-secondary">
                <div class="stat-mini-value">{{ quick_tiles.submitted }}</div>
                <div class="stat-mini-label">Submitted</div>
            </div>
        </a>

        <a class="tile-link {% if quick_filter == 'pending' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=pending">
            <div class="stat-mini">
                <div class="stat-mini-value">{{ quick_tiles.pending }}</div>
                <div class="stat-mini-label">Pending</div>
            </div>
        </a>

        <a class="tile-link {% if quick_filter == 'scheduled' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=scheduled">
            <div class="stat-mini" style="background: linear-gradient(135deg, #198754 0%, #146c43 100%);">
                <div class="stat-mini-value">{{ quick_tiles.scheduled }}</div>
                <div class="stat-mini-label">Scheduled</div>
            </div>
        </a>

        <a class="tile-link {% if quick_filter == 'need_review' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=need_review">
            <div class="stat-mini" style="background: linear-gradient(135deg, #51216b 0%, #3f1853 100%);">
                <div class="stat-mini-value">{{ quick_tiles.need_review }}</div>
                <div class="stat-mini-label">Need Review</div>
            </div>
        </a>

        <a class="tile-link {% if quick_filter == 'on_hold' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=on_hold">
            <div class="stat-mini" style="background: linear-gradient(135deg, #e6a400 0%, #c48a14 100%);">
                <div class="stat-mini-value">{{ quick_tiles.on_hold }}</div>
                <div class="stat-mini-label">On Hold</div>
            </div>
        </a>

        <a class="tile-link {% if quick_filter == 'alerts' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=alerts">
            <div class="stat-mini" style="background: linear-gradient(135deg, #c00000 0%, #9a0000 100%);">
                <div class="stat-mini-value">{{ quick_tiles.alerts }}</div>
                <div class="stat-mini-label">Alerts</div>
            </div>
        </a>

        <a class="tile-link {% if quick_filter == 'due_today' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=due_today">
            <div class="stat-mini" style="background: linear-gradient(135deg, #cc0000 0%, #a00000 100%);">
                <div class="stat-mini-value">{{ quick_tiles.due_today }}</div>
                <div class="stat-mini-label">Due Today</div>
            </div>
        </a>

        <a class="tile-link {% if quick_filter == 'due_tomorrow' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=due_tomorrow">
            <div class="stat-mini" style="background: linear-gradient(135deg, #b30000 0%, #850000 100%);">
                <div class="stat-mini-value">{{ quick_tiles.due_tomorrow }}</div>
                <div class="stat-mini-label">Due Tomorrow</div>
            </div>
        </a>

        <!-- NEW: Due Next 7d -->
        <a class="tile-link {% if quick_filter == 'due_next_7d' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=due_next_7d">
            <div class="stat-mini" style="background: linear-gradient(135deg, #8B0000 0%, #660000 100%);">
                <div class="stat-mini-value">{{ quick_tiles.due_next_7d }}</div>
                <div class="stat-mini-label">Due Next 7d</div>
            </div>
        </a>

        <!-- NEW: Overdue -->
        <a class="tile-link {% if quick_filter == 'overdue' %}active{% endif %}"
           href="?quick_tech={{ quick_tech }}&quick_filter=overdue">
            <div class="stat-mini" style="background: linear-gradient(135deg, #4a0000 0%, #2d0000 100%);">
                <div class="stat-mini-value">{{ quick_tiles.overdue }}</div>
                <div class="stat-mini-label">Overdue</div>
            </div>
        </a>

    </div>
</div>
```

### Backend additions needed (views.py `_get_quick_tiles`)

```python
from django.utils import timezone
import datetime

today = timezone.localdate()
next_7d = today + datetime.timedelta(days=7)

# Due Next 7d: due within the next 7 days (excludes today, not yet completed)
quick_tiles['due_next_7d'] = base_qs.filter(
    due_date__gt=today,
    due_date__lte=next_7d
).exclude(status__in=['completed', 'cancelled']).count()

# Overdue: past due date, not completed
quick_tiles['overdue'] = base_qs.filter(
    due_date__lt=today
).exclude(status__in=['completed', 'cancelled']).count()
```

And add the filter cases to `_apply_staff_quick_filter`:

```python
elif quick_filter == 'due_next_7d':
    today = timezone.localdate()
    return qs.filter(
        due_date__gt=today,
        due_date__lte=today + datetime.timedelta(days=7)
    ).exclude(status__in=['completed', 'cancelled'])

elif quick_filter == 'overdue':
    today = timezone.localdate()
    return qs.filter(due_date__lt=today).exclude(status__in=['completed', 'cancelled'])
```

---

## Implementation Scope (Option C)

| File | Change |
|---|---|
| `cases/templates/cases/admin_dashboard.html` | Replace 2 rows with 1 combined row (HTML only) |
| `cases/views.py` | Add `due_next_7d` and `overdue` to `_get_quick_tiles()` and `_apply_staff_quick_filter()` |

No model changes. No migrations. No other templates affected.
