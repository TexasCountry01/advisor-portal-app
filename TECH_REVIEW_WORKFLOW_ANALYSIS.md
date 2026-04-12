# Tech Review Workflow Enhancement Analysis

**Date:** April 11, 2026  
**Status:** Proposal — Pending Decision

---

## Problem Statement

Tiffany (Level 3 Tech) no longer needs to review all of Ileana's (Level 1 Tech) cases, but Ileana is not yet a Level 2 Tech. Currently, **all** Level 1 tech cases are forced through quality review — there is no way to bypass this, and no way for any tech to voluntarily request help on a specific case.

Additionally, there is no mechanism for a Level 3 tech (Tiffany) to send a case up to a manager (Chris) for review/help when needed.

---

## Current System Behavior

- All Level 1 tech cases **must** go through `pending_review` status before completion
- Level 1 techs see a **"Submit for Review"** button (no option to complete directly)
- Level 2/3 techs see a **"Mark as Completed"** button (skip review entirely)
- Review requirement is hardcoded based on `user_level == 'level_1'`
- There is no per-user override and no voluntary review request mechanism

### Current Workflow (Level 1 Tech)

```
Case Accepted → L1 Tech works case → Submit for Review → pending_review
    → L2/L3 Tech reviews → Approve / Correct / Request Revisions → completed
```

### Current Workflow (Level 2/3 Tech)

```
Case Accepted → L2/L3 Tech works case → Mark as Completed → completed
```

---

## Proposed Changes

### Part A: Per-User Review Requirement Toggle

**Goal:** Allow admins/managers to configure whether a specific Level 1 tech requires mandatory review on all cases.

#### Approach A1: Boolean Flag on User Model (Recommended)

Add a `requires_level1_review` field (default: `True`) to the User model. When set to `False`, the Level 1 tech gets the same "Mark as Completed" button as Level 2/3 techs and cases skip `pending_review`.

| Component | Change |
|-----------|--------|
| User model | Add `requires_level1_review = BooleanField(default=True)` |
| `mark_case_completed` view | Check flag instead of just `user_level == 'level_1'` |
| `Case.requires_review` property | Respect the new flag |
| case_detail template | Show "Mark as Completed" when flag is `False` |
| Admin user profile page | Add toggle managed by admins/managers |

**Effort:** Small — one migration, ~5 code touch points  
**Risk:** Low — defaults to `True`, so existing behavior unchanged for all current L1 techs

#### Approach A2: Promote to Level 2

Simply change Ileana's `user_level` to `level_2`. Zero code changes, but loses the distinction that she's "not really a Level 2 yet."

**Effort:** Zero — admin action only  
**Risk:** Low, but misrepresents skill level

#### Recommendation

**A1** — it's clean, explicit, and preserves the Level 1 designation while removing the mandatory review gate.

---

### Part B: Voluntary "Send for Review" (Ad-Hoc Help Request)

**Goal:** Allow any tech to optionally send a specific case to a senior tech or manager for review/help, with notes explaining what they need.

#### Approach B1: "Request Review" Button for L1 Techs Only

When a Level 1 tech has `requires_level1_review = False` (from Part A), they see **both** "Mark as Completed" and "Request Review." Clicking "Request Review" opens a modal where they type what help they need and optionally pick a specific reviewer.

**Effort:** Medium  
**Limitation:** Only available to Level 1 techs

#### Approach B2: "Request Review" for All Tech Levels (Recommended)

Same as B1 but available to **any** tech (L1, L2, L3). This covers both scenarios:
- **Ileana → Tiffany:** L1 tech requests help from L3 tech
- **Tiffany → Chris:** L3 tech requests help from manager

| Component | Change |
|-----------|--------|
| Case model | Add optional `requested_reviewer` FK to target a specific reviewer |
| case_detail template | Add "Request Review" button alongside "Mark as Completed" for all techs |
| Request Review modal | Notes field (required) + optional reviewer dropdown (L3 techs + managers) |
| `submit_for_review` view | Accept optional reviewer target and help notes |
| Review panel | Display help request notes and who requested the review |
| Notifications | Notify targeted reviewer (or all L3/managers if none specified) |
| CaseReviewHistory | Track voluntary review requests separately from mandatory reviews |

**Effort:** Medium  
**Benefit:** Covers both Ileana→Tiffany and Tiffany→Chris scenarios

#### Recommendation

**B2** — directly addresses all stated scenarios. The existing `CaseReviewHistory` model already tracks reviewer, notes, and timestamps.

---

## Combined Implementation Summary

### New User Model Field

```
requires_level1_review (BooleanField, default=True)
```

- Managed by **admins and managers** on the user profile page
- Only relevant for Level 1 techs
- When `False`: L1 tech can complete cases directly (but can still request review)

### New Case Model Field

```
requested_reviewer (FK to User, nullable)
```

- Set when a tech voluntarily requests review from a specific person
- Cleared when review is completed

### Updated Button Logic (case_detail template)

| Scenario | Buttons Shown |
|----------|--------------|
| L1 tech, `requires_level1_review = True` | "Submit for Review" (mandatory — current behavior) |
| L1 tech, `requires_level1_review = False` | "Mark as Completed" + "Request Review" |
| L2/L3 tech | "Mark as Completed" + "Request Review" |

### Request Review Modal

- **Notes field** (required): "What help do you need?"
- **Reviewer dropdown** (optional): List of L3 techs + managers. If not specified, notifies all eligible reviewers.

### Permission for the Toggle

Admins and managers can toggle `requires_level1_review`. Level 3 techs cannot — consistent with other user-management controls in the system.

---

## Workflow After Implementation

### Level 1 Tech (Review Required = True) — No Change

```
Case Accepted → Work case → Submit for Review → pending_review → L3 reviews → completed
```

### Level 1 Tech (Review Required = False) — New

```
Case Accepted → Work case → Mark as Completed → completed (direct)
                          → OR Request Review → pending_review → L3 reviews → completed
```

### Any Tech (Voluntary Review) — New

```
Case Accepted → Work case → Request Review (with notes + optional target reviewer)
    → pending_review → Targeted reviewer reviews → Approve / Correct / Revisions → completed
```
