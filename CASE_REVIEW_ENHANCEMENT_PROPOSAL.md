# Proposed Enhancement: Flexible Case Review Workflow

**Date:** April 13, 2026 (Revised)

---

## The Problem

Today, every case worked by a Level 1 technician (e.g., Ileana) **must** be reviewed by a senior technician (e.g., Tiffany) before it can be sent to the member. There is no way around this — it's all or nothing. Level 2 technicians have no review requirement at all.

This creates three issues:

1. **Tiffany is getting bogged down** reviewing all of Ileana's cases, even though Ileana is gaining experience and many of her cases don't need review.
2. **When any technician needs help**, there's no formal way to ask another tech to look at a case and tell them what they need help with.
3. **There's no gradual ramp-up** — a tech either has all cases reviewed or none. There's no way to say "this tech can handle Tier 1 on her own but still needs review on Tier 2."

---

## Key Terminology

| Term | Describes | Values | Example |
|------|-----------|--------|---------|
| **Level** | The technician's experience/rank | Level 1, Level 2, Level 3 | Ileana is a Level 1 Tech |
| **Tier** | The complexity of the case | Tier 1 (routine), Tier 2 (moderate), Tier 3 (complex) | A FERS supplement case is Tier 2 |

**Tier Coverage by Level:**

| Tech Level | Can Work | Default Review Required |
|------------|----------|------------------------|
| Level 1 | Tier 1 only | Yes — all tiers |
| Level 2 | Tier 1, Tier 2 | No — none by default |
| Level 3 | Tier 1, Tier 2, Tier 3 | No — never (senior reviewer) |

---

## Change 1: Make Mandatory Review Optional Per Technician, Per Tier

Add a setting on each technician's profile that controls whether their cases require senior review before being sent out. This applies to both Level 1 and Level 2 technicians. **Review toggles are per-technician, per-tier** — not per-level.

### How it works:

- By default, all **Level 1** technicians require review (nothing changes for new hires)
- By default, all **Level 2** technicians do not currently require review
- An authorized user can turn review on/off for a specific technician at the tier level
- When turned off for a tier, that technician can send cases of that tier out directly — just like a Level 3 tech
- The technician stays classified at their current level (their level doesn't change)
- This setting can be turned back on at any time
- **In-flight cases:** When review is turned back ON for a tech, only newly completed cases require review. Cases already in progress are not affected.

### Per-Technician Toggle Matrix

**Ileana (Level 1 Tech)**

| Tier | Require Review? | Default |
|------|----------------|---------|
| Tier 1 | Yes/No | Yes |

**Monica (Level 2 Tech)**

| Tier | Require Review? | Default |
|------|----------------|---------|
| Tier 1 | Yes/No | No |
| Tier 2 | Yes/No | No |

**New Person (Level 2 Tech)**

| Tier | Require Review? | Default |
|------|----------------|---------|
| Tier 1 | Yes/No | No |
| Tier 2 | Yes/No | No |

### Examples

**Example 1:** Chris turns off mandatory review for Ileana's Tier 1 cases. Ileana can now complete and send out Tier 1 cases on her own. She's still a Level 1 tech, but she's trusted to handle routine cases independently.

**Example 2:** Monica (Level 2 Tech) returns to work and initially requires all of her cases (Tier 1 and 2) to be reviewed. Eventually, Tiffany agrees she can send out Tier 1 on her own, but still requires review on Tier 2. Later, Tiffany allows Monica to send all Tier 1 and 2 cases by herself.

---

## Change 2: Allow Any Technician to Request Help on a Specific Case

Add a "Request Review" option that any technician can use when they want another person to look at a case before it goes out.

### How it works:

- A new **"Request Review"** button appears alongside the existing "Mark as Completed" button
- When clicked, the technician writes a note explaining what help they need
- They can optionally choose who they want to review it — **all technicians are listed as potential reviewers** (any tech can be selected, regardless of level)
- The selected reviewer gets a notification and sees the help request when they open the case
- If no specific reviewer is chosen, all Level 3 techs and administrators are notified
- **Any reviewer who is an Administrator or Manager** (i.e., not working in the portal daily) receives an **email notification** in addition to the in-app notification

### Review Chain and Escalation

- A reviewer who receives a case can **further escalate** it to another technician if they need help. For example: Ileana → Tiffany → Chris
- When a reviewer is done, they have two options:
  1. **Push back to the previous tech** (default) — returns the case to whoever sent it for review, so they can see the feedback and learn
  2. **Release directly** — send the case out to the member without returning it (for urgent cases or simple approvals)
- **Escalation returns in reverse order:** If Chris pushes a case back, it goes to Tiffany. If Tiffany then pushes back, it goes to Ileana. The full review chain is visible in the case history.
- **After review push-back:** When a case is returned to the original tech after review, the tech can release it without triggering another mandatory review cycle (the case is already reviewed).

### Examples

**Example 1:** Ileana is working a case and has a question. She clicks "Request Review," writes "Need help verifying the FERS calculation — the dates seem off," and selects Tiffany. Tiffany gets a notification, reviews the case, and either approves it or sends feedback.

**Example 2:** Tiffany is working a complex case and wants Chris's input. She clicks "Request Review," writes her notes, and selects Chris. Chris gets a notification **plus an email** (since she's an Administrator). Same process.

**Example 3:** Ileana sends a case to Tiffany. Tiffany isn't sure about the calculation either, so she escalates to Chris. Chris reviews, adds notes, and pushes back to Tiffany. Tiffany reviews Chris's input, adds her own notes, and pushes back to Ileana. Ileana sees the full chain of feedback, makes final adjustments, and releases the case.

---

## What This Means Day-to-Day

| Scenario | Before | After |
|----------|--------|-------|
| Ileana finishes a routine Tier 1 case | Must wait for Tiffany to review before it goes out | Can send it out directly (if Tier 1 review is turned off for her) |
| Ileana has a question on a case | No formal way to ask for help — has to message Tiffany separately | Clicks "Request Review," writes what she needs, Tiffany is notified |
| Tiffany needs Chris's input | No formal way to route a case to Chris | Clicks "Request Review," writes what she needs, Chris is notified + emailed |
| Monica returns and needs to ramp up | Either all cases reviewed or none | Tier 1 and Tier 2 toggles set independently as trust is earned |
| A new Level 1 tech is hired | All cases require review | All cases still require review (default behavior unchanged) |

---

## Permissions Model

### Two New Granular Permissions

These are per-user flags, independently grantable and revocable by Administrators and Managers. They are **not** automatically granted based on tech level.

| Permission | What It Controls | Default |
|-----------|-----------------|---------|
| `can_manage_review_settings` | Toggle review on/off for other technicians | Off (granted explicitly) |
| `can_manage_delegates` | Access to delegate management page | Off (granted explicitly) |

**Why this matters:** When a tech is promoted to Level 3, they don't automatically get management capabilities. For instance, if Monica is promoted to Level 3, Administrators/Managers can choose to keep review-setting control solely with Tiffany as team leader. Same for delegate management — a new Level 3 tech doesn't automatically get access to manage delegates.

### Who Controls What

| Action | Who Can Do It |
|--------|--------------|
| Grant/revoke `can_manage_review_settings` | Administrators and Managers |
| Grant/revoke `can_manage_delegates` | Administrators and Managers |
| Toggle review on/off for a technician (per tier) | Users with `can_manage_review_settings`, Administrators, Managers |
| Request a review on a specific case | Any technician |
| Approve, push back, or release a reviewed case | Any technician (the selected reviewer) |

---

## Audit Trail

All actions related to this workflow are fully audit logged:

| Event | What's Recorded |
|-------|----------------|
| Review toggle changed | Who changed it, for which tech, which tier, old value → new value |
| Review requested on a case | Who requested, who was selected as reviewer, the note |
| Review escalated | Who escalated, to whom, the note |
| Review approved / pushed back / released | Who acted, what action, notes |
| Permission granted/revoked | Who granted, for whom, which permission |

---

## Summary

These changes give you the flexibility to:

- **Gradually ramp up** technicians by enabling self-release tier by tier
- **Stop** Tiffany from having to review every one of Ileana's cases
- **Keep** the safety net so any technician can ask for help when they need it
- **Allow** escalation chains (Ileana → Tiffany → Chris) with full visibility
- **Control** who has management permissions independently of tech level
- **Maintain** mandatory review for any new or less experienced technicians
- **Audit** every toggle change, review request, and approval
