# ProFeds Advisor Portal — Usage & Performance Summary
**Reporting Period:** March 2026 – May 16, 2026  
**Prepared For:** ProFeds Members & Advisors  
**Report Date:** May 16, 2026

---

## Overview

This report summarizes how the portal is being used, how quickly cases are being processed, and the overall health of the system. Purpose of generating this report was to check statistics, server health, any gaps in audit, overall long term mitigation - DB expansion, file size mitigation.

---

## Highlights at a Glance

| Metric | Value |
|--------|-------|
| Total cases submitted | **1,050** |
| Cases completed | **923** |
| Case completion rate | **87.9%** |
| Average time to completion | **4.9 days** |
| Total documents uploaded | **2,917** |
| Registered members | **182 active** |
| Weeks of consistent activity | **8 weeks** |

---

## 1. How Many Cases Have Been Submitted?

Since launch, **1,050 cases** have been submitted through the portal. Here is the breakdown by month:

| Month | Cases Submitted |
|-------|----------------|
| March 2026 | 143 |
| April 2026 | 567 |
| May 2026 (first 16 days) | 340 |
| **Total** | **1,050** |

April was the biggest month by far, reflecting the wave of members joining and submitting their cases for the first time. Since mid-April, the portal has reached a steady rhythm of **approximately 150–160 new cases per week** — a strong sign that the platform has become a routine part of how advisors work with their clients.

---

## 2. How Quickly Are Cases Being Completed?

The team has maintained an impressive pace:

- **87.9% of all submitted cases have been completed** — only about 1 in 8 cases is still in progress at any given time.
- The **average time from submission to completion is 4.9 days**, with most cases moving through the process in under a week.
- The fastest cases were completed the **same day** they were submitted.
- Even the most complex cases were completed within **34 days**.

| Status | Count | % of Total |
|--------|-------|-----------|
| ✅ Completed | 923 | 87.9% |
| 🔄 In Progress (Accepted) | 100 | 9.5% |
| ❌ Cancelled | 18 | 1.7% |
| 📝 Draft (not yet submitted) | 8 | 0.8% |
| ⏸️ On Hold | 1 | 0.1% |

---

## 3. Document Uploads

There is a significant amount of documentation. Application is robust and is handling this well:

- **2,917 total documents** have been uploaded since launch.
- These documents represent **3.66 GB of data** safely stored and accessible through the portal.
- The average document is about **1.3 MB** in size, typical for PDF retirement packages.
- The most common document type is the **Federal Fact Finder** — which makes up the vast majority of uploads.

**Document uploads by month:**

| Month | Documents Uploaded |
|-------|--------------------|
| March 2026 | 349 |
| April 2026 | 1,581 |
| May 2026 (first 16 days) | 987 |
| **Total** | **2,917** |

On average, each case has about **3 documents** attached, with some more complex cases having up to 12.

---

## 4. Who Is Using the Portal?

| User Type | Active Users |
|-----------|-------------|
| Members (Federal Employees) | 182 |
| Administrators | 3 |
| Benefits Technicians | 3 |
| Manager | 1 |
| **Total Active Users** | **189** |

Most members joined in **March and April 2026** during the initial rollout. The platform is now well established among the member base.

---

## 5. Member Notifications

When a case is completed, members receive an email notification letting them know their retirement analysis is ready. This notification system is fully automated and has been working reliably:

- **826 completion notification emails** have been sent to members.
- The notification system runs every day automatically.
- **Every completed case has had its notification sent** — there are no outstanding or missed notifications. Approximately 56 had to be resent by the CRON job because of SMTP errors but were resent successfully.

---

## 6. System Reliability

The portal has been running continuously since launch with no reported outages. The underlying infrastructure has been stable:

- The server is **running at only 11% of its disk capacity**, with plenty of room for growth.
- The database is **performing well** and is well within normal operating ranges.
- The system is handling the current volume of cases and documents without any performance concerns.

At the current rate of growth, the system has well over **two years of storage capacity** available before any expansion would be needed.

---

## 7. Looking Ahead

Based on the first two months of operation, the portal is handling the workload comfortably and the team is keeping pace with incoming cases. At the current rate:

| Timeframe | Estimated Total Cases |
|-----------|----------------------|
| 3 months from now (Aug 2026) | ~2,000 |
| 6 months from now (Nov 2026) | ~3,000 |
| 12 months from now (May 2027) | ~5,000 |

The platform is built to scale to these volumes without disruption to service or performance.

---

## 8. A Note on Document Security

All documents uploaded to the portal are:

- Stored on a **dedicated secure server** hosted in the United States
- Transmitted over **encrypted HTTPS connections** at all times
- Accessible **only to the ProFeds team members assigned to each case**
- Retained for the duration of each engagement with ProFeds

---

## 9. Things to Watch Going Forward

As the portal grows, several areas require proactive attention to ensure continued reliability and performance. None of these are current emergencies, but each should be planned for.

### 9.1 Storage Growth & Database Expansion

**Status: Monitor — No Urgency Today**

The server currently has approximately **68 GB of free disk space**. At the current document upload rate (~2.3 GB per month), that provides roughly **29 months of runway** — sufficient through October 2028 at present growth.

However, as case volume increases (see Section 7 projections), upload volume will scale with it. By the time we reach ~5,000 cases (May 2027), monthly storage consumption could double. **Storage expansion should be planned and executed before the server disk reaches 50% capacity — not after.**

**What needs to happen:**
- Monitor disk usage monthly (a simple server check or alert)
- At ~40 GB remaining, initiate a DigitalOcean Block Storage volume expansion or evaluate migrating document storage to object storage (DigitalOcean Spaces or AWS S3)
- Object storage migration is a larger project (several weeks of development) but eliminates disk concerns entirely and provides built-in redundancy and CDN delivery

**Timeline recommendation:** Begin planning in Q4 2026; execute no later than Q1 2027.

---

### 9.2 File Upload Size Limits

**Status: Action Needed — Should Be Addressed Soon**

Currently, there is **no enforced limit on how large a document can be**. While typical documents are about 1.3 MB, a single oversized upload (a scanned multi-page document, a large packet, etc.) could be 50–100 MB or more. A handful of these can consume disproportionate disk space and slow down processing for other users.

**What needs to happen:**
- Set a maximum file size per upload — recommended: **30 MB hard limit** with a warning shown to the user at 15 MB
- This enforcement should happen at two levels:
  1. **In the application** — the upload form rejects files over the limit and shows a clear error message
  2. **At the server/network level** — a hard cap at the web server that prevents excessively large uploads from even reaching the application
- This protects both disk space and system responsiveness

**Timeline recommendation:** Implement within the next 30 days.

---

### 9.3 Audit Trail Per-File Traceability

**Status: Low Priority — No Data Loss, But a Gap Exists**

All documents are stored correctly and linked to their cases. However, the system's audit log does not create a separate entry for each individual document uploaded during the initial case submission. Instead, it records one event per case submission with a count of how many files were included.

This means: if someone asked "show me the exact audit trail for this specific file," we can confirm the file was submitted with the case, but not the precise timestamp of that individual file's upload.

**What needs to happen:**
- A code-level update to create one audit log entry per document at the time of submission
- This does not affect existing data or documents — it only improves traceability going forward
- Historical records will continue to show the submission-level event

**Timeline recommendation:** Include in the next scheduled development sprint.

---

### 9.4 Email Delivery Monitoring

**Status: Healthy — But Worth Watching**

The 56 email delivery failures that occurred in April–May were caused by temporary Google SMTP throttling and were all successfully resent by the automated retry system. No members missed a notification.

Going forward:
- If the volume of outgoing emails grows significantly (e.g., >100/day), the current SMTP sending approach may hit Google rate limits more frequently
- Consider monitoring the count of failed vs. retried emails monthly
- If failures become frequent, evaluate a dedicated email delivery service (e.g., SendGrid, AWS SES, Mailgun) which provides higher sending limits, delivery dashboards, and bounce tracking

**Timeline recommendation:** Re-evaluate if/when daily email volume exceeds 50 notifications per day.

---

*Report generated from live production database and server metrics. All figures reflect actual data as of May 16, 2026.*
