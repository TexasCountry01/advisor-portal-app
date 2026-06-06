# Reporting Recommendations — Advisor Portal
**Analysis Date:** June 6, 2026  
**Basis:** Live production database queried directly via SSH (read-only) — June 6, 2026  
**Audience:** Administrator, Manager  
**Read-only analysis — no production changes made**

---

## Live Production Snapshot (Queried June 6, 2026)

| Metric | Value | vs. May 16 Report |
|--------|-------|-------------------|
| Total cases | **1,502** | +452 in 3 weeks |
| Completed | **1,370** (91.2%) | Up from 87.9% |
| Avg turnaround | **4.3 days** | Improved from 4.9 |
| On-time rate | **99.3%** (1,361/1,370) | New measurement |
| Active technicians doing work | **1** (Tiffany Widelski) | — see below |
| Documents uploaded | **4,155** | +1,238 since May 16 |
| Document storage | **5.18 GB** | +1.52 GB since May 16 |
| Total audit log events | **9,588** | +2,539 since May 16 |
| Active members who have submitted | **91 of 182 (50%)** | New measurement |
| Cases with `retirement_date_preference` set | **0 of 1,502** | Field entirely unused |
| API sync pending | **1,502 of 1,502** | Integration never connected |

### Critical Findings from Real Data

**1. The system is still growing — not plateauing.**  
May 2026 was the highest-volume month yet at **659 cases**, surpassing April's 564. June is on pace for ~690+ at the current rate (136 cases in 6 days). The "plateau" noted in the May report was premature.

**2. Three people have processed all cases; one active technician carries the current load.**  
The full case processing history across all roles and active/inactive status:

| Person | Role | Status | Assigned | Completed | Credits |
|--------|------|--------|----------|-----------|---------|
| Tiffany Widelski | Technician L3 | Active | 1,204 | 1,113 | 1,068.5 |
| Ileana Colón-Varona | Technician L1 | **Inactive** (former) | 236 | 235 | 236.5 |
| Monica Frideley | Technician L2 | **Inactive** (former) | 17 | 17 | 17.0 |
| Chris Kowalik | Administrator | Active | 7 | 7 | 7.0 |
| Nickie Orgler | Manager | Active | 0 assigned | — | — |
| *(unassigned)* | — | — | 38 cases | — | — |

Additionally, **Nickie Orgler (Manager)** accepted 81 cases into the workflow — she is active in the acceptance queue even though cases are not assigned directly to her. Two former technicians (Ileana Colón-Varona and Monica Frideley) contributed 253 completions before leaving. **Today, Tiffany Widelski is the only active technician processing cases**, which remains an operational concentration risk as volume continues growing.

**3. Credits are flat regardless of tier — the credit system is functionally unused.**  
88.3% of all completed cases receive exactly **1.0 credit**. Average credit by tier: Tier 1 = 0.95, Tier 2 = 0.98, Tier 3 = 0.99. Tier 3 cases should be the most complex (and worth 2.0–3.0 credits) but are averaging 0.99. Additionally, 55 completed cases have a credit value of exactly 0.0, which may be intentional or may be data entry errors.

**4. Half the member base has never submitted a case.**  
91 of 182 active members (50%) have submitted zero cases. Of the 91 who have submitted, 18 account for 21+ cases each (heavy users). The top advisor alone accounts for 173 cases (11.5% of all volume).

**5. The `retirement_date_preference` field has zero data.**  
Not a single case (0 of 1,502) has this field populated. The field exists in the model and form but members are not using it.

**6. The API sync to benefits-software was never connected.**  
All 1,502 cases show `api_sync_status = 'pending'`. This is not a failure — it means the integration was never activated — but it is worth noting.

---

## Context: What the Data Shows

The portal is growing faster than expected with a single technician handling all production cases. The 91.2% completion rate and 4.3-day average turnaround are excellent, but with only one operational technician, any absence or capacity constraint creates an immediate backlog. The reporting gaps below are rooted in what's actually in the data — not assumptions.

The following recommendations are grounded in what is actually stored in the production database as of today. Each option includes its data source, the question it answers, and a complexity rating.

---

## Option 1 — Pipeline Health Dashboard (Live)
**Priority: High | Complexity: Low**

### What It Answers
> "Right now, what does the active caseload look like — and where is it stuck?"

### Why It Matters
At 150+ cases/week with **one active technician (Tiffany Widelski) carrying the current workload**, visibility into the live pipeline is critical. Today there are 84 accepted cases in flight, 4 submitted cases in queue, 38 unassigned cases, and 1 case on hold for 31 days with no resolution. There is no dashboard view surfacing these numbers at a glance.

### Data Available in Production Today
- `Case.status` → submitted / accepted / hold / pending_review / completed
- `Case.date_submitted` → how long a case has been waiting
- `Case.date_accepted` → time-to-accept (queue age)
- `Case.assigned_to` → which tech has which cases
- `Case.date_due` → upcoming due dates
- `Case.urgency` → rush vs. standard

### Report Components

| Section | Metric | Signal |
|---------|--------|--------|
| **Queue Age** | Cases submitted but not yet accepted: count + avg hours waiting | Today: 4 queued (all from yesterday) — healthy |
| **Active by Technician** | Cases currently in "accepted" status per tech | Today: all 84 active cases assigned to Tiffany Widelski; 38 unassigned |
| **Due in Next 3 / 7 Days** | Count of cases with `date_due` approaching | Early warning before deadlines pile up |
| **Overdue Cases** | Cases past `date_due` and not completed | 9 late completions in history — monitor trend |
| **On Hold** | Cases in "hold" status + hold reason summary | 1 case on hold for **31 days** — needs attention |
| **Pending Review** | Cases awaiting Level 2/3 review | Currently 0 — can spike quickly |

### Format Options
- **A. Live widget on the admin dashboard** — small summary tiles (no date range needed)
- **B. Dedicated Pipeline Report page** with drill-down to case list for each category

---

## Option 2 — Due Date Compliance Report
**Priority: High | Complexity: Low**

### What It Answers
> "Are cases being completed on time? Which techs and which case types are most often late?"

### Why It Matters
The real data shows a **99.3% on-time completion rate** (1,361 of 1,370 completed cases met their due date), with only 9 late completions. This is excellent — and now there is a baseline. The report would track whether this rate holds as case volume continues climbing. With one technician carrying the load, a single period of illness or leave would break the streak immediately.

### Data Available in Production Today
- `Case.date_due` — the committed due date
- `Case.date_completed` — when it was actually finished
- `Case.assigned_to` — whose responsibility
- `Case.tier` — whether complexity is correlated with lateness
- `Case.urgency` — whether rush cases are actually faster

### Report Components

| Metric | Calculation |
|--------|-------------|
| On-time rate | `date_completed <= date_due` / total completed, expressed as % |
| Avg days early | Mean of `(date_due - date_completed)` where positive (early) |
| Avg days late | Mean of `(date_completed - date_due)` where negative (late) |
| On-time rate by technician | Breakdown of compliance per tech |
| On-time rate by tier | Are Tier 3 cases more often late? |
| On-time rate by urgency | Do rush cases actually meet their deadlines? |
| Trend over time | Weekly on-time % — is it improving or declining? |

### Notes
- `date_due` is currently populated at case submission. Cases without a `date_due` (pre-feature cases) would be excluded.
- This report establishes a service level baseline that will become increasingly important as the member base grows.

---

## Option 3 — Quality Review Analytics Report
**Priority: High | Complexity: Low**

### What It Answers
> "How often are cases coming back with revisions? Is quality improving over time?"

### Why It Matters
169 cases have been submitted for quality review. **153 were approved, 11 had revisions requested, and 6 had corrections needed** — a 90.5% first-pass approval rate. However, since only one technician is active and she is Level 3, the review workflow is primarily being used for escalation rather than L1 oversight. Understanding whether the 9.5% revision rate is improving, stable, or growing is actionable.

### Data Available in Production Today
- `Case.review_status` → approved / revisions_requested / corrections_needed
- `Case.reviewed_by` — which senior tech reviewed
- `Case.reviewed_at` — review turnaround time
- `AuditLog` → `case_review_approved`, `case_review_revisions` events with timestamps
- `Case.assigned_to` — which L1 tech submitted for review

### Report Components

| Section | Metric |
|---------|--------|
| **First-pass approval rate** | % of cases reviewed that were approved without revisions |
| **Revision rate by L1 technician** | Which techs require the most rework? |
| **Avg review turnaround** | `reviewed_at - date` when submitted for review |
| **Review outcomes over time** | Weekly trend: are revisions going up or down? |
| **ProFeds error correlation** | Do reviewed cases have a lower error rate? |

---

## Option 4 — Member / Advisor Activity Report
**Priority: High | Complexity: Low–Medium**

### What It Answers
> "Which advisors are most active? Who hasn't submitted in a while? Are there advisors consistently submitting high-complexity cases?"

### Why It Matters
The real data reveals a stark engagement divide: **91 of 182 active members (50%) have never submitted a single case**. Of the active 91, the top 18 advisors account for 21+ cases each, and the single top advisor (Momodou Bojang, workshop code 'AVL') has submitted 173 cases — 11.5% of total volume. This concentration creates both a relationship-management opportunity and a risk profile worth tracking.

### Data Available in Production Today
- `Case.member` → the advisor who submitted
- `Case.workshop_code` → workshop affiliation
- `Case.tier` → complexity level
- `Case.urgency` → rush frequency
- `Case.date_submitted` → submission recency
- `Case.num_reports_requested` → volume of work per submission
- `AuditLog` → `login` events per member
- `User.last_active` → last portal activity timestamp

### Report Components

| Section | Metric |
|---------|--------|
| **Top advisors by case volume** | Bojang: 173, Dukes: 81, Lavy/McNair: 56 each, Griggers: 46 — top 18 have 21+ cases |
| **Never-submitted members** | 91 of 182 active members (50%) — never submitted a case |
| **Inactive submitters** | Members who have submitted before but not in 30+ days |
| **Rush case frequency by advisor** | 45 rush cases total — which advisors use it most? |
| **Multi-report case rate** | Advisors who most often submit cases with 2+ reports |
| **Workshop code breakdown** | AVL: 173, CFG: 146, SWAN/HFR: 56, DMCG: 48, GWM: 46 — top 15 codes cover ~900 cases |

---

## Option 5 — Credit Distribution & Integrity Report
**Priority: High | Complexity: Low**

### What It Answers
> "Are credits being assigned correctly? Is the credit system reflecting actual case complexity?"

### Why It Matters
The real data reveals a significant anomaly: **88.3% of all cases receive exactly 1.0 credit**, and the average credit value is nearly identical across all three tiers (Tier 1: 0.95, Tier 2: 0.98, Tier 3: 0.99). Tier 3 cases — which are the most complex — should be receiving 2.0–3.0 credits, but they average 0.99. Either the credit system is not being used as intended, or Tier 3 does not actually correspond to higher complexity in practice. Additionally, **55 completed cases carry a 0.0 credit value** — it is unclear whether these are intentional (e.g., cancelled before work began, then completed) or data entry gaps.

### Data Available in Production Today
- `Case.credit_value` → the assigned credit
- `Case.credit_adjustment_reason` → reason for non-default credits
- `Case.tier` → expected to correlate with credit
- `Case.assigned_to` → which tech assigned the credit
- `Case.num_reports_requested` → multi-report cases should have higher credits

### Report Components

| Section | Metric |
|---------|--------|
| **Credit value distribution** | 1.0: 1,327 (88.3%), 1.5: 61 (4.1%), 0.0: 55 (3.7%), 0.5: 48 (3.2%), 2.0: 6, 2.5: 1, None: 4 |
| **Credit by tier (actual vs expected)** | Tier 1 avg: 0.95, Tier 2: 0.98, Tier 3: 0.99 — flat across tiers, not scaling with complexity |
| **Zero-credit completed cases** | 55 cases — intentional or data entry error? |
| **High-credit cases** | Only 7 cases at 2.0+ across all 1,502 cases — nearly unused |
| **Credit trend over time** | Is the distribution changing as new cases come in? |

---

## Option 6 — Retirement Date Proximity Report
**Priority: Low (field currently unused) | Complexity: Low**

### What It Answers
> "Which members have cases tied to retirement dates approaching in the next 30, 60, or 90 days?"

### Why It Matters
**The `retirement_date_preference` field has zero data** — not a single case in 1,502 has this field populated. The field exists in the model and presumably in the submission form, but members are not filling it in. Before building a report on this data, the priority should be understanding why members aren't providing it and whether the form prompts for it clearly.

> **Prerequisite:** Drive adoption of this field before building the report. A form change to make it more prominent (or required for certain case types) would generate the data needed to make this report useful.

### Data Available in Production Today
- `Case.retirement_date_preference` — target date
- `Case.status` — is the case actually done?
- `Case.date_completed` — when completed relative to retirement
- `Case.member` — advisor to follow up with

### Report Components

| Section | Description |
|---------|-------------|
| **30-day window** | Active cases (not completed) where `retirement_date_preference` falls within 30 days |
| **60-day window** | Same for 60 days |
| **90-day window** | Same for 90 days |
| **Cases completed after retirement date** | Historical — cases that took longer than the member's preferred date |
| **Monthly retirement concentration** | How many clients per month have retirement dates? Useful for forward staffing |

> **Note:** This data isn't universally populated — members may not always provide a retirement date. A data quality metric (% of cases with this field populated) would be valuable to track alongside this report.

---

## Option 7 — Hold Analysis Report
**Priority: Medium | Complexity: Low**

### What It Answers
> "Why are cases going on hold, how long do they stay there, and is hold usage increasing?"

### Why It Matters
There is currently **1 case on hold, and it has been sitting there for 31 days** (Case WS000-2026-05-0070). The hold reason indicates it was waiting on a new Fact Finder from the member. There is no report that surfaces aging holds or alerts management when a hold exceeds a threshold. As volume scales, holds could quietly accumulate.

### Data Available in Production Today
- `Case.hold_reason` — free-text explanation
- `Case.hold_start_date` — when the hold began
- `Case.hold_end_date` — expected end (if set)
- `Case.hold_duration_days` — planned duration
- `Case.status_before_hold` — what stage the case was at when placed on hold
- `AuditLog` → `case_held`, `case_resumed` events

### Report Components

| Metric | Description |
|--------|-------------|
| Active holds | Current on-hold cases with reason and duration |
| Hold frequency trend | Weekly count of holds placed — is this growing? |
| Avg hold duration | Actual vs. planned duration |
| Most common hold reasons | Text pattern analysis of `hold_reason` field |
| Tech breakdown | Which techs are placing holds most often? |

---

## Option 8 — Case Reassignment Analysis
**Priority: Low | Complexity: Medium**

### What It Answers
> "How frequently are cases being reassigned, why, and does reassignment affect turnaround time?"

### Why It Matters
29 reassignment events across 1,502 cases (1.9%). Since only one technician is active, these 29 reassignments likely represent admin takeovers rather than tech-to-tech transfers. This report becomes more relevant when a second active technician joins — at that point, load balancing and reassignment patterns become meaningful management signals.

### Data Available in Production Today
- `Case.reassignment_history` → JSON array: `[{from_tech, to_tech, date, reason}]`
- `AuditLog` → `case_reassigned` events (29 recorded)
- `Case.date_accepted`, `Case.date_completed` → does reassignment add days?

### Report Components

| Metric | Description |
|--------|-------------|
| Reassignment rate | % of total cases that were reassigned at least once |
| Reassignments per technician | Who initiates the most reassignments? Who receives them? |
| Avg days added by reassignment | Does a reassignment statistically increase turnaround time? |
| Reason breakdown | Common patterns in reassignment justification |

---

## Option 9 — Advisor Submission Pattern & Engagement Trend
**Priority: High | Complexity: Medium**

### What It Answers
> "Is the member base staying engaged? Are submission rates per advisor stable, growing, or declining week-over-week?"

### Why It Matters
The real data shows an engagement concentration that deserves attention: 50% of members have never submitted, while 18 advisors account for the majority of volume. The top advisor alone has 173 cases. Meanwhile, May was the highest-volume month ever (659 cases), and June is on pace to match it — so the growth is coming from existing heavy users, not new submitters. Understanding who is driving growth and whether inactive members can be activated is the core strategic question.

### Data Available in Production Today
- `Case.member`, `Case.date_submitted` — per-advisor submission history
- `User.last_active` — portal engagement
- `AuditLog` → `login` events

### Report Components

| Metric | Description |
|--------|-------------|
| **Never submitted** | 91 of 182 members (50%) — zero lifetime cases |
| **Submission distribution** | 1 case: 5 advisors; 2-5: 12; 6-10: 25; 11-20: 31; 21+: 18 |
| **Repeat submitter rate** | 86 of 91 active submitters have 2+ cases (94.5% retention once they start) |
| **Weekly unique submitter count** | Is the number of active advisors/week growing? |
| **30-day dormancy list** | Advisors who submitted before but haven't in 30+ days |

---

## Option 10 — System Health & Operations Report
**Priority: Medium | Complexity: Low**

### What It Answers
> "Is the system operating cleanly? Are there growing error conditions or operational anomalies?"

### Why It Matters
Currently operational monitoring requires SSH access. The real data surfaces several items worth watching: SSO failures have grown from 89 (May 16) to **95 (June 6)** — a slow but steady increase. Email failures sit at 57. **65 completed/active cases have zero documents attached** (up from 38 in May — growing). And all 1,502 cases show `api_sync_status = 'pending'` because the benefits-software integration was never activated.

### Data Available in Production Today
- `AuditLog` → `sso_login_failed` (89 through May), `email_notification_failed` (56), `cron_job_executed`
- `Case.api_sync_status` → cases not synced to benefits-software
- `Case.fact_finder_pdf_status` → failed PDF generations
- `CaseDocument` with `file_size = 0` → potential corrupt uploads

### Report Components

| Section | What It Shows |
|---------|--------------|
| SSO failure trend | 95 failures total, growing (+6 since May 16) — is a specific advisor affected? |
| Email failure summary | 57 email failures vs 1,772 sent (3.1% failure rate) |
| API sync backlog | **1,502 cases pending** — integration never activated |
| Zero-document cases | **65 active/completed cases** with no documents (was 38 in May, growing) |
| PDF generation failures | Cases where `fact_finder_pdf_status = 'failed'` |
| Large file anomalies | Storage growing at ~2.3 GB/month; 5.18 GB total |

---

## Summary: Prioritized Build Order

> **Standard:** Every report includes `[ Export to CSV ]` and `[ Download PDF ]` buttons in the report header. The Pipeline Health Dashboard is the only exception (live operational view — no exports).

| Priority | Option | Exports | Highest Value Signal |
|----------|--------|---------|---------------------|
| **1** | Pipeline Health Dashboard | None (live view) | Live queue, aging holds, active case load |
| **2** | Member/Advisor Activity | CSV + PDF | 50% of members never submitted; top-10 advisors |
| **3** | Advisor Engagement Trend | CSV + PDF | Where is the growth coming from? |
| **4** | Credit Distribution & Integrity | CSV + PDF | Credits are flat regardless of tier — is this correct? |
| **5** | Due Date Compliance Report | CSV + PDF | 99.3% on-time — establish baseline before it erodes |
| **6** | Quality Review Analytics | CSV + PDF | 90.5% first-pass approval — trending up or down? |
| **7** | Hold Analysis | CSV + PDF | 1 case on hold 31 days unnoticed |
| **8** | System Health / Ops | CSV + PDF | 65 zero-doc cases, API never connected, SSO failures |
| **9** | Reassignment Analysis | CSV + PDF | Low value now; becomes relevant when 2nd tech onboards |
| **10** | Retirement Date Proximity | CSV + PDF | Zero data — drive field adoption first |

---

## Data Gaps (Confirmed from Live DB)

| Field | Actual State | Impact |
|-------|-------------|--------|
| `retirement_date_preference` | **0 of 1,502 cases populated** | Option 10 report unusable until field is adopted |
| `api_sync_status` | **1,502 of 1,502 = 'pending'** — integration never activated | Sync dashboard would show 100% backlog |
| `is_resubmitted` / `resubmission_count` | **0 cases resubmitted** — feature unused | Resubmission report has no data yet |
| Tier legacy values (`1`/`2`/`3`) | 406 cases still use old format | Tier-based reports need normalization guard |
| `credit_adjustment_reason` | Likely sparse (not queried) | Credit reason analysis may be thin |
| `hold_reason` | Free text, no taxonomy | Hold reason analysis requires text pattern matching |
| `reassignment_history` | JSON array — requires Python-level parsing | Option 8 needs view-layer processing, not raw SQL |

---

## Architecture Notes (If Implemented)

All options are built following the same pattern established in `core/views_reports.py`.

### Standard Report Structure

Every report must include **both export formats** displayed side by side in the report header:

```
[ ↓ Export to CSV ]   [ ↓ Download PDF ]
```

This applies to all existing and new reports — including retroactively to any report that currently has only one or neither.

| Component | Pattern |
|-----------|---------|
| **Data function** | `get_[report]_data(date_from, date_to, filters)` — Django ORM only |
| **HTML view** | `@login_required` + `is_admin()` check → renders template |
| **CSV export** | Handled inline via `?export=csv` query param on the same view, returns `HttpResponse(content_type='text/csv')` |
| **PDF view** | Separate `[report]_pdf` view → WeasyPrint `HTML(string=...).write_pdf()` → `HttpResponse(application/pdf)` |
| **PDF template** | Separate `[report]_pdf.html` with inline CSS only (no Bootstrap CDN) |
| **URL routes** | Two routes per report: `reports/[slug]/` and `reports/[slug]/pdf/` in `core/urls.py` |
| **Header buttons** | Both buttons present in top-right of every report, params forwarded: `?export=csv&date_from=...&date_to=...` |
| **Navigation card** | Card added to Specialized Reports section of `view_reports.html` |

### Export Button Template Pattern

```html
<div class="col-md-4 text-end">
    <div class="d-flex gap-2 justify-content-end">
        <a href="?export=csv&date_from={{ date_from }}&date_to={{ date_to }}" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-download"></i> Export CSV
        </a>
        <a href="{% url '[report]_pdf' %}?date_from={{ date_from }}&date_to={{ date_to }}" class="btn btn-sm btn-outline-danger" target="_blank">
            <i class="bi bi-file-earmark-pdf"></i> Download PDF
        </a>
        <a href="{% url 'view_reports' %}" class="btn btn-sm btn-outline-secondary">← Back to Reports</a>
    </div>
</div>
```

### Reports Requiring Retroactive PDF Addition

The following existing reports have CSV but need PDF added:

| Report | CSV | PDF | Status |
|--------|-----|-----|--------|
| ProFeds Error Tracking | ✅ | ✅ | Complete |
| Technician Productivity | ✅ | ✅ | Complete |
| Member Portal Feedback | ✅ (none) | ❌ | Needs PDF |
| Main Reports CSV export | ✅ | — | CSV only by design (aggregate export) |

### Pipeline Health Dashboard exception

The Pipeline Health Dashboard (`/reports/pipeline/`) is a **live operational view** — it has no date range and data changes by the minute. It does not have PDF or CSV exports; a manual refresh button is sufficient.

No new migrations, no new models, and no new dependencies are required for any of the options above. All data already exists in production.
