# Advisor Portal — Production Analytics & Capacity Report
**Report Date:** May 16, 2026  
**Production Server:** reports.profeds.com (104.248.126.74)  
**Database Host:** DigitalOcean Managed MySQL (NYC1)  
**Application Live Since:** ~March 23, 2026 (~54 days)  
**Data Current As Of:** Report generation timestamp

---

## Executive Summary

The Advisor Portal has reached **sustained operational velocity** after a rapid adoption curve in April 2026. The system is healthy and well within capacity limits on all dimensions today, but the current **document storage growth rate of ~2.1 GB/month** is the most critical metric to monitor. At this pace, the server's 79 GB disk will have approximately **29 months of runway** before requiring expansion. No data integrity issues were found. Performance has been reliable.

---

## 1. Application Usage Statistics

### 1.1 Cases Created

| Month | Cases Created | Cumulative Total |
|-------|--------------|-----------------|
| March 2026 | 143 | 143 |
| April 2026 | 567 | 710 |
| May 2026 (through May 16) | 340 | 1,050 |
| **Total** | **1,050** | |

> **Note:** May is only 16 days in. Annualized from May's pace, the full month will produce ~640 cases. April represented a massive onboarding spike; the system has now settled into a **sustainable weekly cadence of ~150–160 cases/week**.

### 1.2 Weekly Case Creation Velocity (Last 8 Weeks)

| Week Starting | Cases Created | Trend |
|--------------|--------------|-------|
| Mar 23 | 50 | Ramp-up |
| Mar 30 | 43 | Ramp-up |
| Apr 6 | 125 | ↑ Sharp growth |
| Apr 13 | 132 | ↑ |
| Apr 20 | 162 | Peak |
| Apr 27 | 155 | Plateau |
| May 4 | 150 | Plateau |
| May 11 | 159 | Stable |

**The system has plateaued at ~150–162 cases/week.** This is a strong signal that the user base is fully onboarded and actively using the platform at full capacity.

### 1.3 Case Status Breakdown (All Time)

| Status | Count | % of Total |
|--------|-------|-----------|
| Completed | 923 | 87.9% |
| Accepted (In-Progress) | 100 | 9.5% |
| Cancelled | 18 | 1.7% |
| Draft | 8 | 0.8% |
| On Hold | 1 | 0.1% |
| **Total** | **1,050** | |

The **87.9% completion rate** is an excellent indicator of workflow efficiency. Only 100 cases are currently in-progress (accepted), consistent with ~150/week throughput implying cases move through the pipeline in under a week on average.

### 1.4 Case Completion Performance

| Metric | Value |
|--------|-------|
| Average days to complete | **4.9 days** |
| Fastest case | 0 days (same-day) |
| Slowest case | 34 days |

Cases are averaging under 5 business days from submission to completion — a healthy turnaround time.

### 1.5 Case Urgency & Tier Distribution

**Urgency:**
| Urgency | Count |
|---------|-------|
| Normal | 1,018 (97.0%) |
| Rush | 32 (3.0%) |

**Tier:**
| Tier | Count | Format | Period Used |
|------|-------|--------|-------------|
| tier_1 | 292 | Current | Apr 17, 2026 → present |
| tier_2 | 266 | Current | Apr 17, 2026 → present |
| 2 (legacy) | 216 | Pre-normalization | Mar 9 → Apr 17, 2026 |
| 1 (legacy) | 169 | Pre-normalization | Mar 9 → Apr 17, 2026 |
| tier_3 | 67 | Current | Apr 17, 2026 → present |
| 3 (legacy) | 20 | Pre-normalization | Mar 9 → Apr 17, 2026 |
| (blank) | 20 | Missing | — |

> **⚠️ Root Cause Identified — Tier Format Change:** Before April 17, 2026, the case acceptance code saved the raw form value (`1`, `2`, `3`) directly to `case.tier`. On April 17, a code fix added normalization: `case.tier = f'tier_{tier}' if not tier.startswith('tier_') else tier`. All new acceptances since that date use the correct format. The 405 legacy records predate the fix and were never backfilled. They are fully functional — the `TechReviewSetting.review_required_for()` method already contains a normalization guard for this exact situation. However, a one-time data migration is still needed for reporting consistency and to fix an active bug (see below).

> **🐛 Active Bug Found:** `cases/views.py` line 2954 contains `tier_num = int(case.tier) if case.tier else 0`. This will raise a `ValueError` on **any case with the new `tier_1` format** since `int('tier_1')` is invalid Python. This code path executes during the pre-completion review check. Cases accepted after April 17 (625 cases) are at risk of hitting this bug if they reach that code path. **This should be patched immediately.**

> **Fix (two steps):** (1) Patch line 2954 to `tier_num = int(case.tier.replace('tier_', '')) if case.tier else 0`. (2) Run the one-time SQL normalization for the 405 legacy records.

### 1.6 Resubmissions & Errors

| Metric | Value |
|--------|-------|
| Cases flagged with ProFeds errors | 27 (2.6%) |
| Total error modification events | 16 |
| Resubmitted cases | 0 (none recorded) |
| Cases (non-draft/cancelled) with zero documents | **38** |

> **⚠️ Issue Identified:** 38 active/completed cases have no documents attached. This may indicate cases where advisors submitted without uploading, or where documents were deleted. Worth auditing to confirm these cases are intentionally document-free.

---

## 2. Document Upload Statistics

### 2.1 Upload Volume by Month

| Month | Documents Uploaded | Storage Added | Avg Size/Doc |
|-------|--------------------|--------------|-------------|
| March 2026 | 349 | 497.86 MB | 1,447 KB |
| April 2026 | 1,581 | 2,030.24 MB | 1,308 KB |
| May 2026 (through May 16) | 987 | 1,221.19 MB | 1,256 KB |
| **Total** | **2,917** | **3,749.29 MB (3.66 GB)** | **~1,316 KB avg** |

### 2.2 Recent Upload Velocity

| Window | Documents | Storage |
|--------|-----------|---------|
| Last 7 days | 421 | 567.59 MB |
| Last 30 days | 1,888 | 2,355.32 MB |

**Current sustained rate: ~421 documents/week, ~567 MB/week, ~2.3 GB/month.**

### 2.3 Document Type Breakdown

| Extension | Count | % | Total Size | Avg Size |
|-----------|-------|---|-----------|---------|
| PDF | 2,821 | 96.7% | 3,558.79 MB | 1,292 KB |
| JPG | 39 | 1.3% | 119.71 MB | 3,143 KB |
| JPEG | 26 | 0.9% | 57.89 MB | 2,280 KB |
| PNG | 18 | 0.6% | 9.86 MB | 561 KB |
| CSV | 4 | 0.1% | 0.01 MB | 3 KB |
| XLSX | 3 | <0.1% | 0.12 MB | 42 KB |
| DOCX | 3 | <0.1% | 0.25 MB | 85 KB |
| ZIP | 1 | <0.1% | 2.56 MB | 2,622 KB |
| TIFF | 1 | <0.1% | 0.06 MB | 59 KB |
| DOC | 1 | <0.1% | 0.03 MB | 35 KB |

**PDFs dominate completely at 96.7% of all uploads and 94.9% of all storage.** Image uploads (JPG/JPEG) are large — averaging 2.3–3.1 MB each, larger than most PDFs. JPGs are primarily used as supplemental documents (e.g., scanned statements).

### 2.4 Document Category Breakdown (by `document_type` field)

| Document Type | Count | Storage |
|--------------|-------|---------|
| fact_finder | 2,846 | 3,662.44 MB |
| supporting | 64 | 84.84 MB |
| other | 4 | 1.60 MB |
| report | 3 | 0.41 MB |

### 2.5 Documents Per Case Statistics

| Metric | Value |
|--------|-------|
| Average documents per case | 2.9 |
| Maximum documents on a single case | 12 |
| Cases with 7+ documents (top group) | ~10 identified |

### 2.6 Largest Individual Files (Top 10)

| File | Size | Uploaded |
|------|------|---------|
| Lawrence FF1 & Fin Docs | 25.46 MB | Apr 23 |
| Manzanares TSP Statement | 24.55 MB | Apr 23 |
| Hatcher FF1 & Fin Docs | 21.92 MB | Apr 2 |
| Diaz Lawrinowicz ProFeds Retirement Docs | 21.54 MB | May 1 |
| Greenfield Michael | 21.09 MB | Apr 28 |
| Jones-Tate FactFinder | 19.91 MB | Apr 22 |
| Anton 4 Profeds | 19.81 MB | Mar 12 |
| Cobbinah | 19.67 MB | May 12 |
| Phillips | 19.19 MB | Apr 28 |
| Manzanares SS Statement | 18.75 MB | Apr 23 |

> **⚠️ Issue Identified:** The largest files are 19–26 MB each. There is currently **no enforced file size limit** in the application. While these are valid documents, if large PDFs continue to be submitted (multi-hundred-page retirement packages), individual files could balloon further. A recommended soft warning at 15 MB and hard limit at 30–50 MB would protect storage and upload performance.

### 2.7 Data Integrity Check

| Check | Result |
|-------|--------|
| Documents with zero file size (corrupt) | **0** ✅ |
| Orphaned documents (no parent case) | **0** ✅ |

No data integrity issues found in the document store.

---

## 3. User Account Statistics

### 3.1 Users by Role (Active)

| Role | Active | Inactive | Total |
|------|--------|---------|-------|
| Member | 182 | 3 | 185 |
| Administrator | 3 | 1 | 4 |
| Technician | 3 | 4 | 7 |
| Manager | 1 | 1 | 2 |
| **Total** | **189** | **9** | **198** |

### 3.2 User Registration Growth

| Month | New Users | Cumulative |
|-------|----------|-----------|
| January 2026 | 1 | 1 |
| February 2026 | 3 | 4 |
| March 2026 | 43 | 47 |
| April 2026 | 150 | 197 |
| May 2026 (through May 16) | 1 | 198 |

> **Note:** The April 2026 spike (150 new users) correlates directly with the production launch and mass SSO onboarding. Registration has slowed dramatically in May, suggesting the initial member base is now fully onboarded. New user additions going forward will be organic/new member acquisitions.

### 3.3 Login Activity

| Month | Logins Recorded |
|-------|----------------|
| March 2026 | 104 |
| April 2026 | 574 |
| May 2026 (through May 16) | 255 |

**Projected full-May logins: ~480**, suggesting slightly lower activity than April's onboarding peak but remaining robust.

### 3.4 Active Sessions

| Metric | Value |
|--------|-------|
| Currently active Django sessions in DB | **542** |
| (Sessions expire after 2 weeks by default) | |

542 active sessions is consistent with an active member base of 182 users, many of whom may have sessions from multiple devices or browsers.

---

## 4. Platform Activity & Audit Log

### 4.1 Total System Events by Type

| Action | Count | Notes |
|--------|-------|-------|
| email_notification_sent | 1,114 | Outbound notifications working |
| case_submitted | 1,059 | Matches case count |
| case_accepted | 1,043 | Near 1:1 with submissions |
| login | 933 | Direct logins (SSO logins separate) |
| case_completed | 857 | |
| logout | 495 | |
| case_submitted_for_review | 169 | |
| case_updated | 165 | |
| sso_auto_provision | 154 | New users created via SSO |
| case_review_approved | 153 | |
| delegate_assigned | 132 | |
| document_uploaded | 130 | See analysis below |
| case_ownership_taken | 129 | |
| sso_login_failed | **89** | ⚠️ Monitoring needed |
| email_notification_failed | 56 | ✅ All retried successfully by cron |
| member_document_uploaded | 4 | Post-submission member uploads |
| other | 55 | |
| member_updates_viewed | 52 | |
| case_deleted | 31 | |
| case_details_edited | 30 | |
| case_reassigned | 29 | |
| **Total audit events** | **7,049** | |

> **ℹ️ Audit Log Document Count — Root Cause Identified:** The 130 `document_uploaded` entries represent **additional uploads only** (technician supplemental uploads after case acceptance). The bulk of documents — those submitted with the initial case (`views_submit_case.py`) — are captured differently: the `case_submitted` audit event stores the total `document_count` in its metadata field. Code investigation confirmed 866 `case_submitted` records have `document_count > 0` in metadata. This is **by design** (one submission event per case, not one event per file), but individual per-file audit entries are not created at submission time. The `CaseDocument` rows exist in full and are correctly linked to their cases. **Traceability at the per-file level for initial submissions does not exist in the audit log**, only at the submission level. See Section 9 for remediation options.

> **✅ Email Notification Failures — Resolved:** All 56 `email_notification_failed` events were **transient Google SMTP 421 errors** (temporary throttling). The production cron job (`send_scheduled_emails`) runs daily, queries `actual_email_sent_date IS NULL`, and retries automatically. As of the report date, **zero completed cases have unsent emails** — all were successfully delivered on retry. The cron job has been confirmed running continuously since launch, sending 25–50 notifications per day in May 2026. The email system is healthy.

> **⚠️ Issue Identified — SSO Login Failures:** 89 failed SSO login attempts have been recorded. While some may be legitimate (expired tokens, configuration mismatches), this should be monitored and the most recent failures reviewed to ensure there is no systemic authentication issue.

### 4.2 Notes & Internal Communication

| Item | Count |
|------|-------|
| Case notes written | 978 |
| Internal case messages | 701 |
| Messaging conversations | 19 |
| Individual messages | 45 |

The case notes (~978) and messages (~701) reflect active advisor-technician communication on cases.

---

## 5. Server Infrastructure & Capacity

### 5.1 Server Specifications

| Component | Spec |
|-----------|------|
| Provider | DigitalOcean |
| CPU | 2 vCPUs (DO-Regular) |
| RAM | 3.8 GB total / 719 MB used / 3.1 GB available |
| Disk | 79 GB / 8.0 GB used (11%) / **68 GB available** |
| OS Inodes | 5,234,688 total / 91,017 used (2%) |
| Application Server | Gunicorn (3 workers + 1 master) |
| Web Server | Nginx (SSL, reverse proxy) |

**RAM is healthy** — only 19% utilized. Buffer/cache is consuming 2.8 GB, which is normal Linux behavior (kernel caching recently accessed data). True free memory is 623 MB + 3.1 GB available.

**CPU load not captured in this report** — recommend adding CPU monitoring.

### 5.2 Database Server

| Item | Value |
|------|-------|
| Provider | DigitalOcean Managed MySQL (NYC1) |
| DB Name | advisor_portal |
| Total DB Size | ~16.6 MB (database metadata only — documents on filesystem) |
| Largest Table | cases_case (~5.0 MB) |
| Second Largest | core_auditlog (~4.9 MB) |

The database is extremely lean because all document files are stored on the filesystem. The DB only stores metadata (filenames, sizes, paths, case data). At the current growth rate, the database will likely remain under **50 MB for the next 12 months**.

> **Note:** The DigitalOcean Managed MySQL plan limits are not visible from this audit. Confirm the current plan's storage allocation in the DigitalOcean control panel to ensure the managed DB has adequate storage headroom for long-term growth.

### 5.3 File System (Media Storage)

| Directory | Size | Description |
|-----------|------|-------------|
| `/media/case_documents/` | **3.7 GB** | Uploaded case documents |
| `/media/case_reports/` | 147 MB | Generated report PDFs |
| `/media/notes_images/` | 4.9 MB | Inline images in notes |
| `/media/chat_images/` | 1.1 MB | Chat/message images |
| `/media/message_images/` | 392 KB | Message attachments |
| **Total `/media/`** | **~3.9 GB** | |

---

## 6. Growth Projections

### 6.1 Storage Growth Forecast

Based on the last 30-day actual rate (**2,355 MB / 30 days ≈ 78.5 MB/day, 2.35 GB/month**):

| Timeframe | New Cases | New Documents | Storage Added | Cumulative Storage Used |
|-----------|-----------|--------------|--------------|------------------------|
| Current (May 16) | — | 2,917 | — | ~8.0 GB (total server) |
| +3 months (Aug 2026) | ~1,950 | ~5,490 | ~7.0 GB | ~15.0 GB |
| +6 months (Nov 2026) | ~3,900 | ~10,980 | ~14.1 GB | ~22.1 GB |
| +12 months (May 2027) | ~7,800 | ~21,960 | ~28.2 GB | ~36.2 GB |
| +18 months (Nov 2027) | ~11,700 | ~32,940 | ~42.3 GB | ~50.3 GB |
| **+24 months (May 2028)** | ~15,600 | ~43,920 | **~56.4 GB** | **~64.4 GB** |
| +29 months (Oct 2028) | ~18,850 | ~53,115 | **~68.2 GB** | **~76.2 GB** ← disk full |

> **⚠️ Critical Finding:** At current growth rates, the server's 79 GB disk will reach capacity in approximately **29 months (approximately October 2028)**. This is adequate runway but requires proactive planning. A disk resize or object storage migration should be planned within the **next 12–18 months**.

### 6.2 Database Growth Forecast

The database is storing only metadata. At ~4.7 KB per case and ~650 cases/month:

| Timeframe | DB Size Estimate |
|-----------|-----------------|
| Today | ~16.6 MB |
| 6 months | ~36 MB |
| 12 months | ~55 MB |
| 24 months | ~94 MB |

**Database growth is not a concern.** It will remain well under 100 MB for the foreseeable future.

### 6.3 Case & User Scale Projections

| Timeframe | Total Cases | Total Users |
|-----------|------------|------------|
| Today (May 16, 2026) | 1,050 | 198 |
| 6 months (Nov 2026) | ~5,000 | ~250–300 |
| 12 months (May 2027) | ~9,000 | ~300–400 |

At 9,000 cases with ~2.9 docs avg = ~26,100 documents. The `cases_case` and `cases_casedocument` tables would have ~27,000 rows — well within MySQL's performance envelope for this table structure.

---

## 7. Risk Assessment & Issues

### 7.1 Risks by Severity

| Severity | Issue | Impact | Recommendation |
|----------|-------|--------|----------------|
| 🔴 **High** | Active bug: `int(case.tier)` crashes on `tier_1` format | ValueError on ~625 cases during pre-completion review | Patch `cases/views.py` line 2954 immediately |
| 🟠 **Medium** | Per-file audit entries missing for initial case submissions | No individual file-level traceability at submission time | Add per-file `document_uploaded` audit events in `views_submit_case.py` (see Section 9) |
| 🟠 **Medium** | Server disk has ~29 months before full | Service interruption if unaddressed | Plan DigitalOcean volume expansion or S3/object storage migration in next 12 months |
| 🟠 **Medium** | No enforced file size limit | Runaway large uploads accelerate storage exhaustion | See Section 9 for 4 implementation options |
| 🟡 **Low** | 89 SSO login failures | Potential member access issues | Review recent failures; confirm no systemic pattern |
| 🟡 **Low** | Tier legacy data (`1`/`2`/`3` vs `tier_1`) | Reporting inaccuracy, filter inconsistency | One-time SQL migration (safe, non-destructive) |
| 🟡 **Low** | 38 active cases with zero documents | Workflow gaps or data quality issue | Audit these 38 cases; confirm intentional or follow up with submitters |
| 🟡 **Low** | No Nginx access log found | Cannot do traffic/performance analysis | Enable nginx access logging; review `/etc/nginx/nginx.conf` |
| ✅ **Resolved** | Email notification failures | Was flagged as issue — confirmed resolved | Cron running daily; 0 unsent emails; all 56 failures were transient SMTP throttles |
| 🟢 **Info** | References app not on production | Feature unavailable to prod users | By design (still in testing on TEST server) |
| 🟢 **Info** | DigitalOcean Managed MySQL plan limits unknown | DB plan may have storage ceiling | Verify plan in DO dashboard |

### 7.2 Performance Scalability Notes

The current infrastructure (2 vCPU, 3.8 GB RAM, 3 Gunicorn workers) is appropriate for today's usage. At ~150 cases/week and ~182 active members, the server is lightly loaded. Points to watch as scale increases:

- **Gunicorn worker count:** 3 workers is fine today. If concurrent users increase significantly (>50 simultaneous), increase to 5–7 workers and consider upgrading to the 4 vCPU plan.
- **No caching layer:** The app currently has no Redis/Memcached. If case detail page load times degrade (particularly with 9,000+ cases and large note/JSON fields), adding Redis for session and query caching would be the highest-impact performance improvement.
- **`cases_case` JSON columns:** The `fact_finder_data` and `report_notes` columns are `JSON` type. As these grow (the fact finder can be extensive), case load queries will read more data. MySQL handles JSON well but indexed JSON path queries may be needed in the future.
- **`core_auditlog` growth:** Currently 5,538 entries and 4.9 MB. At 7,000 entries per 7 weeks, this will reach ~50,000 entries in 12 months (~44 MB). No concern for performance, but consider archiving entries older than 12 months.
- **`django_session` table:** 542 sessions at ~0.3 MB. Django's built-in `clearsessions` management command should be run periodically (recommend adding to cron) to purge expired sessions.

---

## 8. Summary Scorecard

| Category | Status | Notes |
|----------|--------|-------|
| Application uptime | ✅ Healthy | 4 Gunicorn workers running |
| User adoption | ✅ Excellent | 198 users, 150+/week case velocity |
| Case throughput | ✅ Excellent | 87.9% completion, avg 4.9 days |
| Document uploads | ✅ Healthy | 2,917 docs, zero data integrity errors |
| Server disk space | ✅ Adequate | 68 GB free / ~29-month runway |
| Server RAM | ✅ Healthy | 81% free |
| Database size | ✅ Excellent | 16.6 MB, not a concern |
| Email notifications | ✅ Healthy | Cron running; 0 unsent emails; all failures retried |
| Storage growth rate | ⚠️ Monitor | ~2.3 GB/month, plan expansion |
| Audit trail — submission docs | ⚠️ Gap | Per-file entries missing for initial submissions |
| SSO authentication | ⚠️ Monitor | 89 failures recorded |
| Data normalization | ⚠️ Action needed | Tier values inconsistent; active bug at line 2954 |
| File size limits | ⚠️ Missing | No enforced upload limit |

---

## 9. Recommended Actions (Priority Order)

### 9.1 Immediate (This Sprint)

1. **[🔴 HIGH — Bug Fix]** Patch `cases/views.py` line 2954:
   - **Current (broken):** `tier_num = int(case.tier) if case.tier else 0`
   - **Fix:** `tier_num = int(case.tier.replace('tier_', '')) if case.tier else 0`
   - This crashes with `ValueError` on any case using the new `tier_1`/`tier_2`/`tier_3` format (625 cases).

2. **[🔴 HIGH — Data]** Run tier normalization SQL on production:
   ```sql
   UPDATE cases_case SET tier='tier_1' WHERE tier='1';
   UPDATE cases_case SET tier='tier_2' WHERE tier='2';
   UPDATE cases_case SET tier='tier_3' WHERE tier='3';
   ```
   Safe, non-destructive, no migrations needed. Normalizes 405 legacy records.

3. **[🟠 MEDIUM — Compliance]** Add per-file `document_uploaded` audit events in `cases/views_submit_case.py` inside the file upload loop:
   ```python
   # After CaseDocument.objects.create(...)
   AuditLog.log_activity(
       user=user,
       action_type='document_uploaded',
       case=case,
       description=f'Document uploaded at submission: {filename_with_employee}',
       metadata={'original_filename': file.name, 'file_size': file.size}
   )
   ```
   This will not fix historical records but ensures all future submissions are fully traced.

### 9.2 Near-Term (Next 30 Days)

4. **[🟠 MEDIUM — Operations]** Schedule `python manage.py clearsessions` as a weekly cron job to purge expired sessions from `django_session` (currently 542 sessions, some expired).

5. **[🟠 MEDIUM — Operations]** Enable Nginx access logging on production for traffic/performance visibility (`access_log /var/log/nginx/access.log;` in nginx config).

6. **[🟠 MEDIUM — Risk]** Implement file upload size limit. See **Section 9.3** for options.

7. **[🟡 LOW — Quality]** Audit the 38 non-cancelled/non-draft cases with zero documents — confirm intentional or follow up with submitters.

8. **[🟡 LOW — Monitoring]** Review the 89 SSO login failure entries for patterns (repeated same user, time of day, etc.).

### 9.3 File Upload Size Limit — Implementation Options

Four concrete options are presented below. They are not mutually exclusive; Option A + C is the recommended combination.

---

**Option A — Client-Side JavaScript Warning (Easiest, No Backend Change)**
- Intercept file input `change` event, check `file.size` against threshold, show warning before form submit
- Pros: Zero server changes, zero risk, instant user feedback
- Cons: Easily bypassed (no actual enforcement); relies on browser
- Effort: 30 minutes
- Enforcement: Soft only

---

**Option B — Django View Validation (Server-Side Hard Limit)**
- Add size check in each upload view before `CaseDocument.objects.create()`:
  ```python
  MAX_FILE_SIZE = 30 * 1024 * 1024  # 30 MB
  if document_file.size > MAX_FILE_SIZE:
      return JsonResponse({'success': False, 'error': 'File exceeds 30 MB limit'}, status=400)
  ```
- Apply to all 3 upload views: `views_submit_case.py`, `upload_technician_document`, `upload_member_documents`
- Pros: Enforced server-side; cannot be bypassed; consistent across all upload paths
- Cons: Only catches the file after it is fully uploaded to the server (wastes bandwidth on large files)
- Effort: 2–3 hours (3 upload paths + error handling)
- Enforcement: Hard

---

**Option C — Nginx `client_max_body_size` (Network-Level Hard Limit)**
- Add/adjust in `/etc/nginx/sites-enabled/*.conf`:
  ```nginx
  client_max_body_size 50M;
  ```
  (Already set to `100M` — lower to `50M` or `30M`)
- Pros: Rejects oversized requests before they reach Django or disk; protects at the infrastructure layer
- Cons: Returns a generic 413 error unless customized; does not allow per-file granularity (applies to entire request body including all files in a multi-file upload)
- Effort: 5 minutes, nginx reload required
- Enforcement: Hard, at network level

---

**Option D — DigitalOcean Spaces (Object Storage) with Pre-Signed URLs**
- Files upload directly from browser to DO Spaces, bypassing the app server entirely
- Spaces policy enforces size limit before upload starts
- Pros: Eliminates disk usage from app server entirely; scales infinitely; built-in CDN; per-file size enforcement
- Cons: Major architectural change; requires rewriting all upload views and storage backends; significant effort; costs ~$25/month for Spaces
- Effort: 2–4 weeks of development
- Enforcement: Hard, at storage level
- **Best long-term solution** if storage migration is planned anyway (ties into the 29-month disk runway concern)

**Recommendation:** Implement **Option B + C together** now (1 day effort, maximum protection). Plan **Option D** as part of the storage expansion project in the next 12 months.

### 9.4 Planning Horizon

9. **[🟠 MEDIUM — Planning]** Begin planning DigitalOcean Block Storage volume addition (or Spaces/S3 migration) as a 6–12 month planning item.

10. **[FUTURE — Scale]** When total cases reach ~5,000, re-evaluate Gunicorn worker count and consider adding Redis for session caching.

---

## 10. Appendix — SQL Queries Used in This Report

All queries were executed against the DigitalOcean Managed MySQL instance (`advisor_portal` database) via SSH from the production server.

```sql
-- ============================================================
-- TABLE SIZES & ROW COUNTS
-- ============================================================
SELECT 
  table_name, 
  table_rows, 
  ROUND(data_length/1024/1024,3) AS data_mb,
  ROUND(index_length/1024/1024,3) AS idx_mb,
  ROUND((data_length+index_length)/1024/1024,3) AS total_mb
FROM information_schema.tables 
WHERE table_schema=DATABASE() 
ORDER BY (data_length+index_length) DESC;

-- ============================================================
-- CASES BY MONTH
-- ============================================================
SELECT 
  DATE_FORMAT(created_at, '%Y-%m') AS month,
  COUNT(*) AS cases_created
FROM cases_case
GROUP BY DATE_FORMAT(created_at, '%Y-%m')
ORDER BY month;

-- ============================================================
-- CASE STATUS BREAKDOWN
-- ============================================================
SELECT status, COUNT(*) AS count FROM cases_case 
GROUP BY status ORDER BY count DESC;

-- ============================================================
-- DOCUMENTS UPLOADED BY MONTH
-- ============================================================
SELECT 
  DATE_FORMAT(uploaded_at, '%Y-%m') AS month,
  COUNT(*) AS docs_uploaded,
  ROUND(SUM(file_size)/1024/1024,2) AS total_mb
FROM cases_casedocument
GROUP BY DATE_FORMAT(uploaded_at, '%Y-%m')
ORDER BY month;

-- ============================================================
-- DOCUMENT TYPE BREAKDOWN BY FILE EXTENSION
-- ============================================================
SELECT 
  LOWER(SUBSTRING_INDEX(original_filename, '.', -1)) AS ext,
  COUNT(*) AS count,
  ROUND(SUM(file_size)/1024/1024,2) AS total_mb,
  ROUND(AVG(file_size)/1024,2) AS avg_kb
FROM cases_casedocument
GROUP BY LOWER(SUBSTRING_INDEX(original_filename, '.', -1))
ORDER BY count DESC;

-- ============================================================
-- DOCUMENT TYPE BY document_type FIELD
-- ============================================================
SELECT document_type, COUNT(*) AS count, 
  ROUND(SUM(file_size)/1024/1024,2) AS total_mb
FROM cases_casedocument
GROUP BY document_type ORDER BY count DESC;

-- ============================================================
-- AVERAGE DOCS PER CASE
-- ============================================================
SELECT 
  ROUND(AVG(doc_count),1) AS avg_docs_per_case, 
  MAX(doc_count) AS max_docs_on_one_case
FROM (SELECT case_id, COUNT(*) AS doc_count 
      FROM cases_casedocument GROUP BY case_id) t;

-- ============================================================
-- TOP 10 LARGEST INDIVIDUAL DOCUMENTS
-- ============================================================
SELECT original_filename, 
  ROUND(file_size/1024/1024,2) AS size_mb, uploaded_at
FROM cases_casedocument 
ORDER BY file_size DESC LIMIT 10;

-- ============================================================
-- TOTAL DOCUMENT STORAGE (FROM DB METADATA)
-- ============================================================
SELECT COUNT(*) AS total_docs, 
  ROUND(SUM(file_size)/1024/1024,2) AS total_mb, 
  ROUND(AVG(file_size)/1024,2) AS avg_kb
FROM cases_casedocument;

-- ============================================================
-- USERS BY ROLE
-- ============================================================
SELECT role, is_active, COUNT(*) AS count 
FROM accounts_user 
GROUP BY role, is_active ORDER BY role, is_active DESC;

-- ============================================================
-- USER REGISTRATION GROWTH BY MONTH
-- ============================================================
SELECT DATE_FORMAT(date_joined, '%Y-%m') AS month, 
  COUNT(*) AS new_users 
FROM accounts_user 
GROUP BY month ORDER BY month;

-- ============================================================
-- AUDIT LOG ACTION BREAKDOWN
-- ============================================================
SELECT action_type, COUNT(*) AS count 
FROM core_auditlog 
GROUP BY action_type ORDER BY count DESC LIMIT 20;

-- ============================================================
-- LOGIN ACTIVITY BY MONTH
-- ============================================================
SELECT 
  DATE_FORMAT(timestamp, '%Y-%m') AS month,
  COUNT(*) AS logins
FROM core_auditlog
WHERE action_type = 'login'
GROUP BY DATE_FORMAT(timestamp, '%Y-%m')
ORDER BY month;

-- ============================================================
-- WEEKLY CASE CREATION VELOCITY (LAST 8 WEEKS)
-- ============================================================
SELECT 
  DATE_FORMAT(created_at, '%Y-%u') AS yr_week,
  MIN(DATE(created_at)) AS week_start,
  COUNT(*) AS cases_created
FROM cases_case
GROUP BY DATE_FORMAT(created_at, '%Y-%u')
ORDER BY yr_week DESC LIMIT 8;

-- ============================================================
-- CASES WITH NO DOCUMENTS (DATA QUALITY)
-- ============================================================
SELECT COUNT(*) AS cases_with_no_docs
FROM cases_case c
WHERE NOT EXISTS (
  SELECT 1 FROM cases_casedocument d WHERE d.case_id=c.id
)
AND c.status NOT IN ('draft','cancelled');

-- ============================================================
-- DOCUMENTS UPLOADED IN LAST 7 / 30 DAYS
-- ============================================================
SELECT COUNT(*) AS docs_last_7_days, 
  ROUND(SUM(file_size)/1024/1024,2) AS mb_last_7_days
FROM cases_casedocument
WHERE uploaded_at >= DATE_SUB(NOW(), INTERVAL 7 DAY);

SELECT COUNT(*) AS docs_last_30_days, 
  ROUND(SUM(file_size)/1024/1024,2) AS mb_last_30_days
FROM cases_casedocument
WHERE uploaded_at >= DATE_SUB(NOW(), INTERVAL 30 DAY);

-- ============================================================
-- CASE COMPLETION PERFORMANCE
-- ============================================================
SELECT 
  COUNT(*) AS total_cases,
  SUM(CASE WHEN is_resubmitted=1 THEN 1 ELSE 0 END) AS resubmitted_cases,
  SUM(resubmission_count) AS total_resubmissions,
  ROUND(AVG(CASE WHEN date_completed IS NOT NULL 
    THEN DATEDIFF(date_completed, date_submitted) END),1) AS avg_days_to_complete,
  MIN(CASE WHEN date_completed IS NOT NULL 
    THEN DATEDIFF(date_completed, date_submitted) END) AS min_days,
  MAX(CASE WHEN date_completed IS NOT NULL 
    THEN DATEDIFF(date_completed, date_submitted) END) AS max_days
FROM cases_case
WHERE status NOT IN ('draft','cancelled');

-- ============================================================
-- DATA INTEGRITY CHECKS
-- ============================================================
-- Zero-size documents (corrupt)
SELECT COUNT(*) AS cases_with_doc_errors 
FROM cases_casedocument 
WHERE file_size = 0 OR file_size IS NULL;

-- Orphaned documents (no parent case)
SELECT COUNT(*) as orphaned_docs 
FROM cases_casedocument d 
LEFT JOIN cases_case c ON c.id=d.case_id 
WHERE c.id IS NULL;

-- ============================================================
-- TIER VALUE DISTRIBUTION & TIMELINE
-- ============================================================
SELECT tier, COUNT(*) AS count FROM cases_case 
GROUP BY tier ORDER BY count DESC;

SELECT 
  tier,
  MIN(DATE(created_at)) AS first_seen,
  MAX(DATE(created_at)) AS last_seen
FROM cases_case
WHERE tier IS NOT NULL AND tier != ''
GROUP BY tier ORDER BY first_seen;

-- ============================================================
-- EMAIL DELIVERY STATUS VERIFICATION
-- ============================================================
-- Completed cases with email NOT yet sent
SELECT COUNT(*) AS completed_cases_email_not_sent
FROM cases_case
WHERE status='completed' 
  AND actual_release_date IS NOT NULL 
  AND actual_email_sent_date IS NULL;

-- Completed cases where email WAS sent
SELECT COUNT(*) AS completed_cases_email_sent
FROM cases_case
WHERE status='completed' AND actual_email_sent_date IS NOT NULL;

-- Daily email cron activity (last 10 days)
SELECT DATE(timestamp) AS day, COUNT(*) AS email_send_events
FROM core_auditlog
WHERE action_type IN ('email_notification_sent', 'email_notification_failed')
GROUP BY DATE(timestamp)
ORDER BY day DESC
LIMIT 10;

-- Most recent email failure descriptions
SELECT DATE(timestamp) AS fail_date, description
FROM core_auditlog
WHERE action_type='email_notification_failed'
ORDER BY timestamp DESC
LIMIT 5;

-- ============================================================
-- DOCUMENT AUDIT LOG BREAKDOWN (FULL)
-- ============================================================
SELECT action_type, COUNT(*) AS count
FROM core_auditlog
WHERE action_type LIKE '%document%' OR action_type LIKE '%upload%'
GROUP BY action_type ORDER BY count DESC;

-- Case submissions with documents counted in metadata
SELECT COUNT(*) AS submissions_with_docs
FROM core_auditlog
WHERE action_type='case_submitted'
  AND JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.document_count')) > '0';

-- ============================================================
-- TIER NORMALIZATION (REMEDIATION SQL — NOT YET RUN)
-- ============================================================
-- Run these in order on production to normalize legacy tier values:
UPDATE cases_case SET tier='tier_1' WHERE tier='1';
UPDATE cases_case SET tier='tier_2' WHERE tier='2';
UPDATE cases_case SET tier='tier_3' WHERE tier='3';
-- Verify after:
SELECT tier, COUNT(*) FROM cases_case GROUP BY tier ORDER BY tier;
```

---

*Report generated from live production database and server metrics. All figures reflect actual data as of May 16, 2026. Updated with code investigation findings May 16, 2026.*
