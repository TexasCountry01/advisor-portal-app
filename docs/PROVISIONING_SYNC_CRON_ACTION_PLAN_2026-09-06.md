# Provisioning Sync — Daily Alert Email & GHL Deactivation Detection
## Action Plan
Date: 2026-09-06
Status: Planning — no code changes yet. For review/confirmation before implementation begins.

---

## 0. GHL scope check — no new scopes needed

Before starting, confirmed that everything in this plan is covered by the two scopes already granted to the `Advisor Portal Sync` Private Integration Token (`contacts.readonly` and `locations/customFields.readonly`):

| Requirement | GHL call | Scope | Status |
|---|---|---|---|
| New GHL contact detection | `GET /contacts/` | `contacts.readonly` | Already have it |
| Missing-tag detection (deactivation candidates) | `GET /contacts/` or `GET /contacts/{id}` | `contacts.readonly` | Already have it |
| Delegate-request GHL cross-check | Email lookup against fetched contacts | `contacts.readonly` | Already have it |
| Workshop/Member Code display | `GET /locations/{id}/customFields` | `locations/customFields.readonly` | Already have it |

No write scope (`contacts.write`) is needed — by design (see Decision #8), the system only detects and alerts; a human always takes the actual provisioning/deactivation action. No webhook/real-time scope is needed either — this is a polling design (nightly cron), not the webhook-based real-time option discussed and explicitly deferred in `docs/GHL_SYNC_ANALYSIS_2026-08-29.md`. **Chris does not need to change anything in GHL to support this plan.**

---

## 1. What already exists (foundation to build on)

This app already has the building blocks needed — this is additive work, not a rewrite:

| Piece | Location | Reusable for this feature? |
|---|---|---|
| GHL contact fetch + tag-based filtering | `accounts/ghl_client.py` (`fetch_ghl_contacts`), `accounts/sso.py` (`determine_role_from_tags`) | Yes — same functions the manual "Sync from GHL" button uses today |
| Manual sync/matching UI | `accounts/views.py` (`sync_ghl_contacts`), `accounts/templates/accounts/ghl_sync.html` | Yes — this cron automates what that page currently requires a click to do |
| Standard email pattern (HTML+TXT, audit-logged) | `cases/services/email_service.py` (`send_email_notification`), `cases/templates/emails/*.html` + `*.txt` | Yes — this is "the standard template we've been using" and should be followed |
| Management-command-as-cron pattern | `cases/management/commands/release_scheduled_cases.py`, `send_scheduled_emails.py`, documented in `CRON_JOB_SETUP.md` | Yes — same pattern (Django management command + crontab/Task Scheduler entry) |
| Configurable settings singleton | `core/models.py` `SystemSettings` (e.g. `feedback_email_1`/`feedback_email_1_enabled` pattern, `batch_email_enabled`) | Yes — new settings fields belong here |
| Existing delegate-request flow | `core/views.py` (`request_add_delegate`, `_send_delegate_request_email`), `accounts/models.py` (`DelegateRequest`) | Partially — sends an email today, but does **not** check GHL at all yet |
| Audit trail | `core/models.py` `AuditLog` | Yes — every alert/notification should be logged the same way other emails are |

**Nothing here requires touching the calculation/case logic** — this is scoped entirely to `accounts` (provisioning) + a new scheduled job.

---

## 2. Restating the requirements (as I understand them)

### A. Daily digest email
- Runs once a day, ~6:00 AM.
- Subject: **"Portal Access Changes - Action Required"** (count goes in the **body**, not the subject — see Decision #3 below).
- Configurable recipient email address(es) — added to `SystemSettings`, following the existing `feedback_email_1`/`feedback_email_1_enabled` pattern.
- Uses the same visual template style as other system emails (`cases/templates/emails/*.html`).
- **Only sends if there's something to report.** No open items → no email.

### B. "New" vs "still open" tracking
- If the job finds 8 unmatched GHL contacts today, and the same 8 are still unmatched tomorrow, they should **not** look brand-new again tomorrow.
- The system needs to remember **when each discrepancy was first detected**, and:
  - Show that "first detected" date in the email and on the GHL Sync Review panel.
  - Only badge something as "**NEW**" if it was first detected since the last run (i.e., genuinely new since yesterday).
  - Automatically stop reporting an item once it's resolved (provisioned, tag restored, or user deactivated).

### C. Two directions of drift to detect
1. **New GHL contact with a portal-access tag, not yet provisioned in advisor-portal** (already partly visible today via the manual "Sync from GHL" → Unmatched Contacts table).
2. **NEW: Active advisor-portal user whose GHL record no longer carries a portal-access tag** — i.e., access was revoked in GHL, but nobody deactivated the corresponding portal account yet. Email should include short deactivation instructions.

### D. Delegate-request cross-check
- When a member requests a delegate (`request_add_delegate`), the email to staff should be enhanced to say one of:
  - *"No GHL contact record exists for this email — create one first."*
  - *"A GHL contact record exists ([contact_id]) but has no portal access tag — apply the Member or Delegate tag."*
  - *(implicitly) "Tag already present — proceed with adding the delegate assignment in the portal."*
- This requires looking up the requested delegate's email against GHL contacts (reusing `fetch_ghl_contacts`) at the time of the request.

---

## 3. Decisions — confirmed 2026-09-06

1. **Recipient config: up to three emails.** `SystemSettings` gets `provisioning_alert_email_1/2/3` + a matching `_enabled` toggle for each (extends the original two-field proposal to three, per confirmation).
2. **Timezone: Central Time.** Confirmed — this app always operates in Central Time (America/Chicago) for all scheduling. The cron runs at 6:00 AM Central.
3. **Subject line confirmed exactly:** `Portal Access Changes - Action Required` — no dynamic count in the subject; counts appear in the email body per section.
4. **"No email if nothing open" applies across both categories** (new-contact detection AND missing-tag detection) — confirmed.
5. **Always list all currently-open items — confirmed, and keep the two categories in clearly separate sections** of the same email (not merged into a single combined list), each with its own heading, table, and count. "NEW" badges apply only to genuinely new entries within a section.
6. **Delegate-request GHL check enriches the existing instant staff email** — confirmed. It does not move into the daily digest; the daily digest may still separately reference any delegate requests still unresolved after some days (see open item below).
7. **Missing-tag detection scope — clarified below**, since this needs a concrete example rather than an abstract confirmation.
8. **Cron only alerts — confirmed.** No automatic provisioning, tag changes, or deactivation is ever performed by the system itself; a human always takes the action after reading the email.
9. **Always write an audit log — confirmed (new requirement).** Every cron run writes an `AuditLog` entry summarizing the result (new/still-open/resolved counts, whether an email was sent), regardless of outcome — including "no-op" runs where nothing was open and no email was sent. Every delegate-request GHL enrichment also logs what was found. This follows the exact pattern already used for `sso_sync`, `email_notification_sent`, etc.

### Clarifying #7 — scope of missing-tag detection

The underlying question: should the daily "missing GHL tag" check look at **every** active portal user, or only some of them?

Here's why it can't be "every active user" without modification — a concrete walk-through:

| User | Role | Has a GHL portal-access tag today? | Should this ever alert? |
|---|---|---|---|
| Jane Advisor | `member` | Yes (`Portal access: Member`) | No — fine, no alert |
| Sam Delegate | `member`, `is_pure_delegate=True` | Yes (`Portal access: Delegate`) | No — fine, no alert |
| Pat Advisor | `member` | **No — tag was removed in GHL** | **Yes — this is exactly the case we want to catch** |
| Terry Tech | `technician` | No — **and never will**, by design | **No — this is expected, not a problem** |
| Alex Admin | `administrator` | No — **and never will**, by design | **No — this is expected, not a problem** |

`technician`/`manager`/`administrator` accounts are **never** expected to carry a GHL portal-access tag — the whole point of `PORTAL_MANAGED_ROLES` in `accounts/sso.py` is that staff roles are assigned inside the portal, not driven by GHL tags at all. If the missing-tag check looked at *all* active users without this distinction, **every single staff account would trigger a false "needs deactivation" alert, every single day**, permanently drowning out the real signal (Pat Advisor).

So: **scoping the check to `role='member'` isn't a narrowing of "active users" — it's the precise set of users for whom a missing tag is actually meaningful**, since `role='member'` already covers both plain advisors and pure delegates (delegates are stored as `role='member'` with `is_pure_delegate=True` — there's no separate "delegate" role in this app's data model). Staff roles are correctly and permanently excluded because a missing tag is their *normal, expected, permanent state* — not a signal of anything.

**Recommendation: scope to `role='member'`, active users only.** This is not a compromise — it's the only scope that produces a meaningful signal.

---

## Remaining open item (not yet confirmed)
- **"Delegate requests still unresolved after N days"** — item #6 mentions the daily digest may reference stale/unresolved delegate requests. What counts as "unresolved" (status remains `pending` on `DelegateRequest`?) and what's N (e.g., 2 business days)? This can be deferred to a later phase if you'd rather not decide now — the core plan (categories C.1/C.2 + enriched instant delegate email) does not depend on resolving this.

---

## 4. Proposed architecture

### 4.1 New model: `ProvisioningAlert`
Purpose: persist "first detected" / "still open" / "resolved" state across daily runs — this is what answers requirement B directly.

```python
# accounts/models.py (new)
class ProvisioningAlert(models.Model):
    ALERT_TYPES = [
        ('new_ghl_contact', 'New GHL Contact Not Provisioned'),
        ('missing_ghl_tag', 'Active Portal User Missing GHL Tag'),
    ]

    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    contact_id = models.CharField(max_length=100, blank=True, null=True)   # GHL contact id, when known
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='provisioning_alerts')

## 4. Proposed architecture

### 4.1 New model: `ProvisioningAlert`
Purpose: persist "first detected" / "still open" / "resolved" state across daily runs — this is what answers requirement B directly.

```python
# accounts/models.py (new)
class ProvisioningAlert(models.Model):
    ALERT_TYPES = [
        ('new_ghl_contact', 'New GHL Contact Not Provisioned'),
        ('missing_ghl_tag', 'Active Portal User Missing GHL Tag'),
    ]

    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    contact_id = models.CharField(max_length=100, blank=True, null=True)   # GHL contact id, when known
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='provisioning_alerts')
    email = models.EmailField(blank=True)
    details = models.JSONField(default=dict)     # name, workshop_code, ghl_role, tags snapshot, etc.

    first_detected_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)     # bumped every run it's still open
    resolved_at = models.DateTimeField(null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('alert_type', 'contact_id', 'user')
```

Lifecycle each run:
- **Not seen before** → create with `first_detected_at=now` → this run's email marks it "**NEW**".
- **Seen before, still open** → `last_seen_at` updates, no "NEW" badge, still included in the digest.
- **No longer detected** (provisioned, tag restored, or account deactivated) → set `resolved_at=now`, excluded from future emails automatically. Self-healing — no manual cleanup needed.

This single table answers requirement B precisely, and doubles as the data source for a "First Detected" column + "NEW" badge on the existing GHL Sync Review page.

### 4.2 New shared service module: `accounts/services/provisioning_sync.py`
Extract the detection logic into one place used by **both** the manual "Sync from GHL" page and the new cron job — avoiding duplicating GHL-fetch/matching logic a third time:

```python
def compute_new_ghl_contacts():
    """Category C.1 — GHL contacts with a portal tag, not in the User table."""
    # Reuses fetch_ghl_contacts() + determine_role_from_tags(), same as sync_ghl_contacts view

def compute_missing_tag_users():
    """Category C.2 — active, role='member' Users whose GHL contact (by contact_id
    or email fallback) no longer carries a portal access tag, or has no GHL contact at all."""

def sync_provisioning_alerts():
    """Run both detections, upsert ProvisioningAlert rows (create/update/resolve),
    return (new_alerts, still_open_alerts) for the caller (cron or view) to use."""
```

The existing `sync_ghl_contacts` view gets a small refactor to call into this shared module rather than duplicating fetch/match logic inline — reducing future maintenance to one place.

### 4.3 New management command: `accounts/management/commands/sync_provisioning_alerts.py`
Following the exact pattern of `release_scheduled_cases.py` / `send_scheduled_emails.py`:

```python
class Command(BaseCommand):
    help = 'Detect GHL/portal provisioning drift and email staff if anything needs attention'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        # 1. Check SystemSettings toggle (provisioning_alerts_enabled) -- skip if off
        # 2. sync_provisioning_alerts() -> upserts ProvisioningAlert table
        # 3. Always write an AuditLog entry summarizing the run (new/still-open/resolved
        #    counts, email sent True/False) -- even a no-op run gets logged
        # 4. If no open alerts at all -> stop here (no email)
        # 5. Render + send digest email via cases/services/email_service.py pattern,
        #    to up to 3 configured recipients
```

### 4.4 New `SystemSettings` fields (`core/models.py`)
Following the existing `feedback_email_*` / `batch_email_enabled` conventions exactly, extended to 3 recipients (confirmed):

```python
provisioning_alerts_enabled = models.BooleanField(default=True, help_text='Enable daily GHL/portal provisioning drift email')
provisioning_alert_email_1 = models.EmailField(blank=True, default='')
provisioning_alert_email_1_enabled = models.BooleanField(default=True)
provisioning_alert_email_2 = models.EmailField(blank=True, default='')
provisioning_alert_email_2_enabled = models.BooleanField(default=False)
provisioning_alert_email_3 = models.EmailField(blank=True, default='')
provisioning_alert_email_3_enabled = models.BooleanField(default=False)
```

### 4.5 New email templates (matching existing visual style)
`accounts/templates/emails/provisioning_alert_digest.html` + `.txt`, styled like `cases/templates/emails/case_released_notification.html` (header banner, sectioned tables, CTA button, footer disclaimer). Two clearly **separate** sections (confirmed — not merged into one combined list), each with its own heading, table, and count:

**Section 1 -- New/Open GHL Contacts Not Yet Provisioned ({{ new_contacts_count }})**
| Name | Email | Workshop | GHL Role | Contact ID | First Detected |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | Sep 5, 2026 NEW |

CTA button -> link directly to the GHL Sync Review page (`/accounts/ghl-sync/`).

**Section 2 -- Active Portal Users Missing GHL Access ({{ missing_tag_count }})**
| Name | Username | Email | First Detected |
|---|---|---|---|
| ... | ... | ... | Sep 4, 2026 |

Followed by a short, standard instructional blurb (as requested):
> **To deactivate:** Go to **Admin Dashboard → User Management**, find the user, and click the deactivate icon next to their row. This preserves their case history and can be reversed at any time via the reactivate icon.

### 4.6 Delegate-request email enrichment (`core/views.py`, `_send_delegate_request_email`)
Add a GHL lookup step before composing the existing instant email:
```python
from accounts.ghl_client import fetch_ghl_contacts
# Look up delegate_request.delegate_email among fetched GHL contacts
# Determine: no_contact_found / contact_found_no_tag / contact_found_with_tag
# Append the appropriate guidance line to the existing email body
```
(Confirmed — this stays part of the *existing instant* email rather than moving into the daily digest.)

### 4.7 GHL Sync Review panel enhancement (`accounts/templates/accounts/ghl_sync.html`)
Add a "First Detected" column (sourced from `ProvisioningAlert.first_detected_at`) and a "NEW" badge when `first_detected_at` is within the current alert window — directly answering "when did the system recognize them as new... on the provision panel."

---

## 5. Cron scheduling (matching existing documentation conventions)

**Linux/Mac** (added to `CRON_JOB_SETUP.md`-style docs):
```cron
# Provisioning drift alert — daily at 6:00 AM Central Time
0 6 * * * cd /home/dev/advisor-portal-app && /home/dev/advisor-portal-app/venv/bin/python manage.py sync_provisioning_alerts >> /var/log/advisor-portal/provisioning_alerts.log 2>&1
```

**Windows Task Scheduler** (LOCAL dev), matching the existing pattern in `CRON_JOB_SETUP.md`:
- Trigger: Daily, 6:00 AM
- Action: `venv\Scripts\python.exe manage.py sync_provisioning_alerts`

Add to both TEST and PROD crontabs once verified (same rollout discipline used for the existing `release_scheduled_cases` job).

---

## 6. Testing & rollout plan

| Phase | Action |
|---|---|
| 1 | Add `ProvisioningAlert` model + migration; add `SystemSettings` fields (3 recipient emails) + migration |
| 2 | Build `provisioning_sync.py` service module; refactor `sync_ghl_contacts` view to use it (no behavior change for the manual page) |
| 3 | Build `--dry-run` support in the new management command, including the always-on audit log entry; run manually on TEST against real GHL data, verify detection counts match the manual Sync page |
| 4 | Build email templates (two separate sections); send a test digest to yourself only (not real recipients) on TEST |
| 5 | Add "First Detected"/"NEW" badge to the GHL Sync Review panel |
| 6 | Enrich the delegate-request instant email with the GHL lookup; test with a real delegate request on TEST |
| 7 | Install the cron job on TEST only (6:00 AM Central), observe for a few real days (confirms "still 8 records tomorrow != still new" behavior with real day-over-day runs) |
| 8 | Once verified, deploy to PROD, configure up to 3 real recipient emails in System Settings, install PROD cron job |

---

## 7. Final status

All decisions are confirmed as of 2026-09-06 (see Section 3). **One item remains genuinely open** and can be deferred to a later phase without blocking the start of implementation:

- **"Delegate requests still unresolved after N days"** referenced under Decision #6 — what counts as unresolved, and what N should be, for the daily digest to optionally reference stale delegate requests. Not required for the core plan (categories C.1/C.2 detection + the enriched instant delegate-request email) to ship.

Ready to begin implementation per the phased rollout plan in Section 6.
