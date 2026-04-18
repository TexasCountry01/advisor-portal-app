# What's New on TEST — Quality Review Workflow & Recent Changes

> **This document covers features currently on the TEST server that are not yet on Production.**  
> The TEST server has a **grey navbar** with a "TEST" badge. Production has the standard **blue navbar**.

---

## The Quality Review System (Biggest Change)

### What It Is

A new quality control layer where cases are reviewed by a senior technician before being released to the member. Whether a case requires review depends on **who is working it** and **what tier** the case is.

### Technician Levels

Every technician is assigned a level:

| Level | Role | Review Behavior (Default) |
|-------|------|--------------------------|
| **Level 1** — New Technician | Does the work | **Must** submit all cases for review before they can be completed |
| **Level 2** — Technician | Does the work, can also review | **Can** complete cases directly without review (but can still optionally submit for review) |
| **Level 3** — Senior Technician | Does the work, can also review | **Can** complete cases directly without review (but can still optionally submit for review) |

### Case Tiers

Each case is assigned a tier when accepted (Tier 1, Tier 2, Tier 3). The review requirement is checked per-tech, per-tier — so a Level 1 tech might require review on Tier 1 cases but an admin could override that specific combination.

### How the System Decides: "Does This Case Need Review?"

The system checks in this order:

1. **Is there an explicit override?** — Admins/managers can set a specific toggle for any tech+tier combination (e.g., "Tech Jane, Tier 2 → no review required"). If an override exists, it wins.
2. **No override? Use the default** — Level 1 techs require review. Level 2 and Level 3 techs do not.

### What the Tech Sees (Based on Their Level)

**Level 1 tech working an accepted case:**
- Sees **"Submit for Review"** and **"Put on Hold"** buttons only
- Does **NOT** see "Mark as Completed" — they cannot complete cases on their own
- Helper text: *"Upload reports and add technical notes, then submit for senior tech review."*

**Level 2 or Level 3 tech working an accepted case:**
- Sees **"Mark as Completed"**, **"Submit for Review"** (optional), and **"Put on Hold"**
- Can either complete the case directly or choose to send it for review
- Helper text: *"Complete the case yourself, or submit for a senior tech to review first."*

### Submit for Review — Step by Step

1. Tech clicks **"Submit for Review"**
2. System validates that all requested reports have been uploaded. If reports are missing, the tech gets a warning but can override and continue.
3. A modal opens with:
   - **Notes** field (optional) — instructions or context for the reviewer
   - **Reviewer** dropdown (optional) — pick a specific L2/L3 tech, or leave blank for any senior tech
4. Tech clicks **Submit**
5. Case status changes to **Pending Review**
6. Notifications are sent to the selected reviewer (or all eligible L2/L3 techs + admins/managers if no specific reviewer was chosen)

### What the Reviewer Sees

When an L2/L3 tech opens a case in **Pending Review** status that is **not assigned to them**, they see three action buttons:

| Button | What It Does |
|--------|-------------|
| **Approve Case** | Marks the case as Completed. Reviewer sets the release date/schedule. The original tech gets a notification that their case was approved. |
| **Request Revisions** | Sends the case back to the original tech with feedback notes. Case returns to Accepted status with a yellow "Needs Revision" banner. The tech must make corrections and resubmit. |
| **Fix & Complete Myself** | Reviewer takes over, makes corrections, and completes the case themselves. |

### The Revision Cycle

When revisions are requested:
- The original tech sees a **yellow banner** at the top of the case showing: reviewer name, review date, and the feedback notes
- A **"Resubmit for Review"** button appears
- The tech makes corrections and resubmits → case goes back to Pending Review

### Managing Review Settings (Admin/Manager Only)

Under **Management → Review Settings**, admins and managers see a table of all technicians with toggle switches per tier:

| Technician | Tier 1 | Tier 2 | Tier 3 |
|------------|--------|--------|--------|
| Jane (L1) | ✅ Required | ✅ Required | ✅ Required |
| Bob (L2) | ❌ Not Required | ❌ Not Required | ❌ Not Required |

- Toggles override the defaults instantly
- Each toggle shows who last changed it and when
- L3 techs can also access this page if granted the **"Can manage review settings"** permission (toggled in Manage Users)

---

## Other Changes on TEST (Not Yet on PROD)

### Dashboard Improvements

- **Sticky column headers** — Table headers stay locked at the top when scrolling through cases
- **Credits column** — New toggleable column in the Columns menu showing each case's credit value, sortable

### Case Detail Changes

- **Inline employee name edit** — Pencil icon next to the employee name heading. Opens a modal to correct the first/last name with a reason. Works on any case status (including completed/released). All changes are audit-logged.
- **Reports requested edit** — Pencil icon next to the "Reports requested" count. Techs can adjust the number (1–9) with a reason.
- **Delete reports** — Trash icon next to each uploaded report. Confirmation required. Removes the file and database record.
- **Image attachments in case chat** — "Attach Image" button next to the message input. Supports PNG, JPEG, GIF, WebP. Preview shown before sending. Images display inline in the chat.
- **Image attachments in general messages** — Same image attachment support in the Messages section (conversations outside of cases).
- **Additional Resources visible to members** — Members can now see tech-uploaded supplementary documents in the Reports & Resources section.
- **Submit for Review modal** — Single unified button replaces the old separate review request buttons. Modal includes optional notes and reviewer selection.

### Environment Indicator

- **TEST** — Grey navbar with yellow "TEST" badge next to the logo
- **PROD** — Standard blue navbar (no badge)

---

## Case Flow Summary

```
                                    ┌─────────────────────┐
                                    │   SUBMITTED         │
                                    │   (new case)        │
                                    └─────────┬───────────┘
                                              │ Tech accepts
                                              ▼
                              ┌───────────────────────────────┐
                              │         ACCEPTED              │
                         ┌────│   (tech working the case)     │────┐
                         │    └───────────┬───────────────────┘    │
                         │                │                        │
                    Put on Hold     L1 tech must          L2/L3 tech can
                         │          submit for             complete directly
                         ▼          review                       │
                    ┌─────────┐         │                        │
                    │  HOLD   │         ▼                        ▼
                    └─────────┘   ┌──────────────┐     ┌──────────────┐
                                  │   PENDING    │     │  COMPLETED   │
                                  │   REVIEW     │     │  (released)  │
                                  └──────┬───────┘     └──────────────┘
                                         │
                              ┌──────────┼──────────┐
                              ▼          ▼          ▼
                         Approved   Revisions   Fix & Complete
                              │     Requested        │
                              │          │           │
                              ▼          ▼           ▼
                         COMPLETED   Back to     COMPLETED
                                    ACCEPTED
                                   (yellow banner,
                                    fix & resubmit)
```
