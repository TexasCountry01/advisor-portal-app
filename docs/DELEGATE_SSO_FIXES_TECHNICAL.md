# Delegate Access & SSO Audit Trail — Technical Fix Report

**Date:** March 3, 2026  
**Commits:** `4d053eb`, `1ea5236`, `ec3367f`  
**Environment:** TEST (`test-reports.profeds.com`)

---

## Summary

Three commits resolved delegate access bugs reported during live testing and a critical audit trail gap discovered during post-fix review. All 13 testers were verified.

---

## Issue 1: Delegates Denied When Viewing Cases (commit `4d053eb`)

**Symptom:** Delegates could see their advisor's cases listed on the dashboard queue, but clicking "View" returned an "Access Denied" error.

**Root Cause:** `case_detail` in `cases/views.py` only checked `case.member == user` for member-role users. It had no logic to look up `MemberDelegate` relationships, so any user who wasn't the case owner was rejected.

**Fix:** Added a secondary check — if the logged-in member is NOT the case owner, query `MemberDelegate.objects.filter(delegate=user, member=case.member)`. If a delegation relationship exists, grant `can_view = True` and `can_edit = True`.

**File:** `cases/views.py` — `case_detail()` (line ~1176)

**Affected Testers:**

| Tester | Workshop | Role | Impact |
|--------|----------|------|--------|
| Frank Dimicelli | CFG | Member + Delegate | Could not view cases for advisors he is delegate for |
| Brandon Dimicelli | CFG | Member + Delegate | Same |
| Jaylon Dukes | CFG | Member + Delegate | Same |
| Dale McGregor | DMCG | Member + Delegate | Same |
| Madison McGregor | DMCG | Member + Delegate | Same |
| Ed Smith | VWP | Member + Delegate | Same |

---

## Issue 2: Dropdown Showing Only Self on Submit Case (commit `4d053eb`)

**Symptom:** On the "Submit New Case" page, delegates who should see a dropdown of their assigned advisors only saw themselves. The advisor dropdown was locked to a single value.

**Root Cause:** The `is_single_choice` flag was set with `len(advisors_list) == 1`, but the template used it to decide whether to render a locked field vs. a dropdown. The problem was actually upstream — the `advisors_list` was being built correctly, but the old logic `is_single_choice = len(advisors_list) == 1` was wrong because it needed `<= 1` to properly handle edge cases. More importantly, the dropdown was collapsing because the template hid it when `is_single_choice` was True.

**Fix:** Changed to `is_single_choice = len(advisors_list) <= 1`. This ensures the dropdown only locks when there is truly 0 or 1 advisor available.

**File:** `cases/views_submit_case.py` — `submit_case()` (line ~63)

**Same 6 testers affected** as Issue 1 (all member+delegate users).

---

## Issue 2b: Document Upload Views Lacking Delegate Support (commit `4d053eb`)

**Symptom:** Delegates attempting to upload documents to their advisor's cases would receive permission errors.

**Root Cause:** Two upload views checked `case.member == user` but had no `MemberDelegate` fallback:
1. `upload_member_documents` (AJAX endpoint)
2. `upload_member_document_to_completed_case` (form-based endpoint)

**Fix:** Added `MemberDelegate.objects.filter(delegate=user, member=case.member).exists()` check to both views, granting upload permission when a delegation relationship exists.

**Files:**
- `cases/views.py` — `upload_member_documents()` (line ~6173)
- `cases/views.py` — `upload_member_document_to_completed_case()` (line ~3092)

**Same 6 testers affected.**

---

## Issue 3: Pure Delegates Seeing Themselves in Advisor Dropdown (commit `1ea5236`)

**Symptom:** Pure delegates (users who are delegates for other advisors but have no cases of their own and no one delegating to them) appeared in their own advisor dropdown on the Submit Case page. They should only see the advisors they are assigned to.

**Root Cause:** When building `advisors_list`, the code checked `if user not in advisors_list` and then added the user unconditionally. There was no check to determine whether the user is also an advisor (has their own cases or has delegates assigned to them) vs. a pure delegate.

**Fix:** Added an `is_also_advisor` check before including the user in the dropdown:
```python
is_also_advisor = (
    MemberDelegate.objects.filter(member=user).exists()
    or Case.objects.filter(member=user).exists()
)
if is_also_advisor:
    advisors_list.insert(0, user)
```

A user is only added to their own dropdown if they either:
- Have at least one delegate assigned to them (they are a member in MemberDelegate), OR
- Have at least one case under their own name

**File:** `cases/views_submit_case.py` — `submit_case()` (line ~49)

**Affected Testers:**

| Tester | Workshop | Role | Impact |
|--------|----------|------|--------|
| Sabra Singleton | CFG | Pure Delegate | Saw herself in dropdown (shouldn't) |
| Janae Lickert | CFG | Pure Delegate | Same |
| Evan Hicks | HFR | Pure Delegate | Same |
| James Lavy | HFR | Pure Delegate | Same |
| Shawn Hicks | HFR | Pure Delegate | Same |
| Les McGregor | DMCG | Pure Delegate | Same |
| Autumn Chartier | DMCG | Pure Delegate | Same |

---

## Issue 4: SSO Audit Events Written to Wrong Database Table (commit `ec3367f`)

**Symptom:** SSO login sync events and auto-provisioning events were not visible in the admin/manager audit trail.

**Root Cause:** `accounts/sso.py` imported `AuditLog` from `accounts.models` (line 24: `from .models import AuditLog`). This is a **different model and database table** (`accounts_auditlog`) from the main audit log used everywhere else (`core.AuditLog` → table `core_auditlog`). The `accounts.AuditLog` has different field names (`action`, `resource_type`, `details`) vs. the `core.AuditLog` fields (`action_type`, `description`, `metadata`, `changes`).

Every SSO login that triggered a profile sync or a new user auto-provision was logged — but to a table that the audit trail views never query.

**Fix:**
1. Changed import in `accounts/sso.py` from `from .models import AuditLog` to `from core.models import AuditLog`
2. Converted both `AuditLog.objects.create()` calls to use `core.AuditLog` field names:
   - `action` → `action_type`
   - `resource_type`/`resource_id` → `related_user`
   - `details` → `metadata` + `changes`
   - Added `description` field

**File:** `accounts/sso.py` (lines 24, 353, 388)

---

## Issue 5: SSO Login Failures Not Logged (commit `ec3367f`)

**Symptom:** When SSO login failed (access denied, token exchange error, unexpected error), nothing was written to the audit trail. An administrator had no visibility into failed login attempts.

**Fix:** Added `AuditLog.objects.create()` calls in `accounts/views_sso.py` for all three exception handlers in `sso_callback()`:
- `SSOAccessDenied` — logged as `sso_login_failed` with `error_type: access_denied`
- `SSOError` — logged as `sso_login_failed` with `error_type: sso_error`
- Generic `Exception` — logged as `sso_login_failed` with `error_type: unexpected`

Each entry captures IP address, user agent, and error message.

**File:** `accounts/views_sso.py` — `sso_callback()` (lines ~118-150)

---

## Issue 6: Missing ACTION_CHOICES for SSO Events (commit `ec3367f`)

**Symptom:** The `core.AuditLog.ACTION_CHOICES` field did not include SSO-specific action types, which would cause Django validation warnings.

**Fix:** Added three new action types to `ACTION_CHOICES` in `core/models.py`:
- `sso_login_failed` — "SSO Login Failed"
- `sso_auto_provision` — "SSO User Auto-Provisioned"
- `sso_sync` — "SSO Profile Synced"

**Migration:** `core/migrations/0014_add_sso_audit_action_types.py`

---

## Issue 7: Delegate Context Missing from Audit Entries (commit `ec3367f`)

**Symptom:** When a delegate submitted a case or uploaded documents on behalf of an advisor, the audit trail showed the action but did not indicate it was performed by a delegate or who they were acting on behalf of.

**Fix:** Added delegate context metadata to three locations:

1. **Case submission** (`cases/views_submit_case.py`): When `user.id != advisor.id`, the audit entry now includes `submitted_by_delegate`, `delegate_id`, `delegate_name`, `delegate_email`, and `on_behalf_of` in metadata. Description changes from "Case submitted for [name]" to "Case submitted for [name] by delegate [delegate] on behalf of [advisor]".

2. **AJAX document upload** (`cases/views.py` — `upload_member_documents()`): When `is_case_delegate` is True, adds `uploaded_by_delegate`, `delegate_id`, `delegate_name`, `on_behalf_of`.

3. **Form-based document upload** (`cases/views.py` — `upload_member_document_to_completed_case()`): Same delegate context fields. Also fixed a missing `description` field on this audit entry.

---

## Complete Tester Verification Matrix

| # | Tester | Workshop | Type | Issue 1 | Issue 2 | Issue 3 | Verified |
|---|--------|----------|------|---------|---------|---------|----------|
| 1 | Frank Dimicelli | CFG | Member+Delegate | ✅ | ✅ | — | ✅ |
| 2 | Brandon Dimicelli | CFG | Member+Delegate | ✅ | ✅ | — | ✅ |
| 3 | Jaylon Dukes | CFG | Member+Delegate | ✅ | ✅ | — | ✅ |
| 4 | Sabra Singleton | CFG | Pure Delegate | — | — | ✅ | ✅ |
| 5 | Janae Lickert | CFG | Pure Delegate | — | — | ✅ | ✅ |
| 6 | Evan Hicks | HFR | Pure Delegate | — | — | ✅ | ✅ |
| 7 | James Lavy | HFR | Pure Delegate | — | — | ✅ | ✅ |
| 8 | Shawn Hicks | HFR | Pure Delegate | — | — | ✅ | ✅ |
| 9 | Dale McGregor | DMCG | Member+Delegate | ✅ | ✅ | — | ✅ |
| 10 | Madison McGregor | DMCG | Member+Delegate | ✅ | ✅ | — | ✅ |
| 11 | Les McGregor | DMCG | Pure Delegate | — | — | ✅ | ✅ |
| 12 | Autumn Chartier | DMCG | Pure Delegate | — | — | ✅ | ✅ |
| 13 | Ed Smith | VWP | Member+Delegate | ✅ | ✅ | — | ✅ |

---

## Files Modified

| File | Changes |
|------|---------|
| `cases/views.py` | Delegate check in `case_detail`, delegate check + context in both upload views |
| `cases/views_submit_case.py` | `is_single_choice` fix, pure delegate exclusion, delegate audit context |
| `accounts/sso.py` | Import fix (`core.models`), field name corrections on 2 audit calls |
| `accounts/views_sso.py` | Added `AuditLog` import, IP helper, 3 failure audit entries |
| `core/models.py` | 3 new `ACTION_CHOICES` entries |
| `core/migrations/0014_add_sso_audit_action_types.py` | Migration for new choices |

---

## Deployment

All three commits deployed to TEST server (`test-reports.profeds.com`) and verified:
- Django system checks: 0 issues
- All migrations applied
- All module imports: OK
- Gunicorn: active and running
- SSO AuditLog confirmed pointing to `core_auditlog` table
