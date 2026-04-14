# Release Notes — April 13, 2026

## Flexible Case Review Workflow

**Branch:** `main` (uncommitted, pending deploy)  
**Base Commit:** `d697982`  
**Type:** Feature — Major Enhancement  

---

### Summary

Replaces the hardcoded "Level 1 always requires review" logic with a fully configurable per-technician, per-tier review system. Adds an ad-hoc review request workflow that allows any technician to request peer review with escalation chain support.

---

### Change Statistics

| Metric | Count |
|---|---|
| Files modified | 8 |
| Files created | 4 |
| Total files touched | 12 |
| Lines added | ~1,288 |
| Lines removed | ~41 |
| Net new lines | ~1,247 |
| New Django models | 2 |
| New views | 6 |
| Modified views | 1 |
| New URL patterns | 6 |
| New migrations | 3 |
| New templates | 1 |
| New audit action types | 6 |
| New notification types | 2 |
| Tests passing | 30/30 |

---

### Files Changed

#### Models

| File | Change |
|---|---|
| `accounts/models.py` | Added `can_manage_review_settings` and `can_manage_delegates` BooleanFields to User model (+11 lines) |
| `cases/models.py` | Added `TechReviewSetting` model, `CaseReviewRequest` model, updated `Case.requires_review` property (+152 lines) |
| `core/models.py` | Added 6 audit action types and 2 notification types to choices (+8 lines) |

#### Views

| File | Change |
|---|---|
| `cases/views.py` | 6 new views + modified `mark_case_completed` (+479 lines) |
| `accounts/views.py` | Updated `delegate_management` permission check (+9/−2 lines) |

#### Templates

| File | Change |
|---|---|
| `cases/templates/cases/case_detail.html` | Request Review button, review requests panel, 2 modals, JavaScript functions (+302 lines) |
| `cases/templates/cases/review_settings.html` | New admin page for per-tech per-tier review toggles (125 lines) |

#### URLs & Migrations

| File | Change |
|---|---|
| `cases/urls.py` | 6 new URL patterns (+10 lines) |
| `accounts/migrations/0018_...py` | User permission fields (18 lines) |
| `cases/migrations/0035_...py` | TechReviewSetting + CaseReviewRequest (47 lines) |
| `core/migrations/0019_...py` | AuditLog + StaffNotification choices (18 lines) |

---

### New Models

#### `TechReviewSetting`
Configures whether a specific technician's work at a specific case tier requires quality review before release.

| Field | Type | Description |
|---|---|---|
| `technician` | FK → User | The technician this setting applies to |
| `tier` | CharField | `tier_1`, `tier_2`, or `tier_3` |
| `requires_review` | BooleanField | Whether review is required |
| `set_by` | FK → User | Admin/manager who set this |
| `updated_at` | DateTimeField | Last modified timestamp |

**Defaults** (when no explicit row exists):
- Tier 1 → Review required
- Tier 2 → Review not required
- Tier 3 → Review not required

**Constraint:** `unique_together = (technician, tier)`

#### `CaseReviewRequest`
Tracks ad-hoc review requests from any technician, with escalation chain support.

| Field | Type | Description |
|---|---|---|
| `case` | FK → Case | The case being reviewed |
| `requested_by` | FK → User | Technician requesting review |
| `reviewer` | FK → User (nullable) | Targeted reviewer, or NULL for "any senior" |
| `notes` | TextField | What the tech needs reviewed |
| `status` | CharField | `pending`, `approved`, `pushed_back`, `released`, `escalated`, `cancelled` |
| `parent_request` | Self-FK (nullable) | Links escalation chains |
| `response_notes` | TextField | Reviewer's response |
| `responded_by` | FK → User (nullable) | Who responded |
| `responded_at` | DateTimeField (nullable) | When responded |
| `created_at` | DateTimeField | Created timestamp |

---

### New Views

| View | Method | URL Pattern | Purpose |
|---|---|---|---|
| `request_review` | POST | `/<case_id>/request-review/` | Tech submits ad-hoc review request |
| `respond_to_review_request` | POST | `/review-request/<id>/respond/` | Reviewer approves, pushes back, releases, escalates, or cancels |
| `get_review_requests` | GET | `/<case_id>/review-requests/` | JSON API for case detail panel |
| `get_eligible_reviewers` | GET | `/api/eligible-reviewers/` | JSON API for reviewer dropdown |
| `review_settings_page` | GET | `/review-settings/` | Admin page for per-tech per-tier toggles |
| `update_review_setting` | POST | `/review-settings/update/` | AJAX toggle endpoint |

### Modified Views

| View | Change |
|---|---|
| `mark_case_completed` | Replaced `case.assigned_to.user_level == 'level_1'` with `case.requires_review` (dynamic per-tech per-tier lookup) |
| `delegate_management` | Now checks `can_manage_delegates` permission for technicians instead of blanket role allow |

---

### New Audit Action Types

| Action Type | When Logged |
|---|---|
| `review_setting_changed` | Admin toggles a per-tech per-tier review setting |
| `review_requested` | Tech submits an ad-hoc review request |
| `review_escalated` | Reviewer escalates a review request to another person |
| `review_pushed_back` | Reviewer pushes back a review request |
| `review_released` | Reviewer releases a case directly to the member |
| `permission_changed` | Admin grants/revokes a user permission |

### New StaffNotification Types

| Notification Type | When Created |
|---|---|
| `review_requested` | Sent to targeted reviewer (or all eligible) when a tech requests review |
| `review_action_taken` | Sent to original requester when their review request is responded to |

---

### UI Changes

#### Case Detail Page
- **"Request Ad-hoc Review" button** — Visible for all tech levels (L1, L2, L3) when case is in `accepted` or `hold` status
- **Review Requests panel** — Sidebar card showing all review requests for the case with status badges, timestamps, and response notes
- **Request Review modal** — Reviewer dropdown (optional), notes textarea
- **Respond to Review modal** — Approve, Push Back, Escalate (with target selector), or Cancel actions

#### Review Settings Page (`/cases/review-settings/`)
- Table of all active technicians with toggle switches per tier
- Shows who set each override and when
- Defaults clearly labeled
- Explanatory info card describing behavior

---

### Behavior Changes

| Before | After |
|---|---|
| Level 1 techs always require review | Review requirement is configurable per-tech per-tier via admin settings |
| Level 2/3 techs never require review | Level 2/3 techs can be configured to require review |
| No way for a tech to request a peer review | Any tech can request an ad-hoc review from a specific person or "any senior" |
| No escalation support | Review requests can be escalated through a chain (e.g., L2 → L3 → Admin) |
| Delegate management open to all technicians | Delegate management requires `can_manage_delegates` permission for technicians |
| Review-related actions had 3 audit types | 9 audit action types covering all review events |

---

### Escalation Chain Example

1. **Ileana** (L1 tech) requests review from **Tiffany** (L2)
2. **Tiffany** escalates to **Chris** (L3) — original request marked `escalated`, new request created with `parent_request` link
3. **Chris** approves — notification sent back to Ileana
4. Full chain visible via `CaseReviewRequest.get_chain()` method

---

### Migration Sequence

```
accounts.0018_user_can_manage_delegates_and_more
  ├── Add field can_manage_delegates to User
  └── Add field can_manage_review_settings to User

cases.0035_casereviewrequest_techreviewsetting
  ├── Create model CaseReviewRequest
  └── Create model TechReviewSetting

core.0019_alter_auditlog_action_type_and_more
  ├── Alter field action_type on AuditLog
  └── Alter field notification_type on StaffNotification
```

---

### Validation

- `python manage.py check` — 0 issues
- `python manage.py makemigrations --check` — No changes detected
- `python manage.py test` — 30/30 passing
- All new URL patterns resolve correctly
- Server starts without errors
