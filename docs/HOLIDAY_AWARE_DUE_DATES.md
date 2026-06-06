# Holiday-Aware Due Date — Implementation Plan

## Background

An advisor submitted feedback requesting that the system account for federal holidays when automatically setting case due dates. The current behavior sets the due date to exactly 7 calendar days from the submission date, which can fall on or immediately after a holiday, reducing the team's effective working window.

**Desired behavior:**
- The system silently extends the due date by 1 calendar day for each federal holiday that falls within the 7-day window.
- The advisor sees the adjusted date with no special highlighting — it is simply presented as the due date, matter-of-factly.
- If the advisor manually changes the date back to the original 7-day mark (i.e., a date inside the holiday window), a small informational message appears:

> *"This due date accounts for the upcoming holiday to ensure our team has adequate time to prepare this report."*

---

## Approved Approach: `python-holidays` + Admin-Managed Overrides

`python-holidays` generates the authoritative US federal holiday list automatically for any year, handling weekend-observance shifts (e.g., July 4 on Sunday → observed Monday). Those holidays are synced into a `Holiday` database table automatically when the admin opens the Holidays section — covering the current year and the next year. The admin can then:

- **Toggle any federal holiday off** — e.g., if Columbus Day is not observed by the team
- **Add custom holidays** — e.g., a one-time office closure
- **Toggle custom holidays on/off** — without deleting them

The `calculate_due_date()` utility queries only **active** holidays in the window, so `python-holidays` drives defaults and admin overrides drive exceptions.

---

## Current System Behavior

The default due date is hard-coded in multiple places:

| Location | Code |
|---|---|
| `cases/views_submit_case.py` line 69 | `timezone.now().date() + timedelta(days=7)` |
| `cases/views_quick_submit.py` line 48 | `timezone.now().date() + timedelta(days=7)` |
| `cases/views_submit_case.py` `api_calculate_rushed_fee` | Hard-coded 7-day baseline |
| `cases/templates/cases/submit_case.html` `checkRushedStatus()` | Compares against `today + 7 days` |

---

## Holiday Model

```python
class Holiday(models.Model):
    date      = DateField(unique=True)
    name      = CharField(max_length=100)
    is_custom = BooleanField(default=False)  # False = synced from python-holidays
    active    = BooleanField(default=True)   # Admin can disable any holiday
```

---

## `calculate_due_date` Logic

```
1. start_date = submission date
2. base_days  = SystemSettings.default_case_due_days (default 7)
3. due        = start_date + base_days

Loop (up to 20 iterations to prevent infinite loops):
    holidays_in_window = Holiday.objects.filter(
        active=True,
        date__gt=start_date,
        date__lte=due
    )
    if no new holidays found: break
    due += timedelta(days=len(new_holidays_found))

4. Return due
```

Handles the edge case where extending the window exposes a second holiday.

---

## Frontend Message Logic

```
holiday_adjusted_date  = value passed from backend context
rush_threshold_date    = today + rush_case_threshold_days

If user picks a date where:
    date < holiday_adjusted_date   (inside extended window — holiday was accounted for)
    AND date >= rush_threshold_date (not a rush case)
→ show informational note:
  "This due date accounts for the upcoming holiday to ensure our
   team has adequate time to prepare this report."
→ do NOT flag as rushed

If user picks a date < rush_threshold_date:
→ existing rush warning (unchanged behavior)

Default date shown to advisor:
→ holiday_adjusted_date, no message, no highlighting
```

---

## Files to Modify

| # | File | Change |
|---|---|---|
| 1 | `requirements.txt` | Add `holidays` package |
| 2 | `core/models.py` | Add `Holiday` model |
| 3 | `core/migrations/0023_holiday.py` | Generated migration |
| 4 | `cases/utils_holidays.py` *(new)* | `get_holidays_in_window()`, `calculate_due_date()`, `sync_federal_holidays()` |
| 5 | `cases/views_submit_case.py` | Use utility; pass `holiday_adjusted_date` + `holidays_in_window` to context |
| 6 | `cases/views_quick_submit.py` | Use utility for default due date |
| 7 | `cases/views_submit_case.py` `api_calculate_rushed_fee` | Use adjusted baseline |
| 8 | `cases/templates/cases/submit_case.html` | JS holiday message logic |
| 9 | `core/views.py` | Holiday CRUD in `system_settings`; auto-sync on Case Defaults tab load |
| 10 | `templates/core/system_settings.html` | Holidays section inside Case Defaults tab |

---

## Admin UI (inside Case Defaults tab)

- Auto-syncs current year + next year from `python-holidays` on page load (no button needed)
- Table of holidays: Date | Name | Source (Federal / Custom) | Active toggle
- "Add Custom Holiday" form: date picker + name field
- Federal holidays show as read-only name with active toggle only
- Custom holidays show with a delete option

---

## Design Decisions

| Decision | Choice |
|---|---|
| Holiday UI placement | Inside existing **Case Defaults** tab in System Settings |
| Auto-sync trigger | Automatic on page load — current year + next year |
| Sync frequency | Only adds missing entries; never overwrites admin's active/inactive choices |
| Rush check baseline | Remains `rush_case_threshold_days` from SystemSettings (unchanged) |
| Holiday message | Informational only — no color, no icon, plain text below the date field |
