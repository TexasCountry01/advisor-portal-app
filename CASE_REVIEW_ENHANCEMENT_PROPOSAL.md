# Proposed Enhancement: Flexible Case Review Workflow

**Date:** April 11, 2026

---

## The Problem

Today, every case worked by a Level 1 technician (e.g., Ileana) **must** be reviewed by a senior technician (e.g., Tiffany) before it can be sent to the member. There is no way around this — it's all or nothing.

This creates two issues:

1. **Tiffany is getting bogged down** reviewing all of Ileana's cases, even though Ileana is gaining experience and many of her cases don't need review.
2. **When Ileana does need help**, there's no way for her to specifically ask Tiffany to look at a case and tell her what she needs help with. The same is true if Tiffany needs Chris to weigh in on a case.

---

## Recommendation

We recommend two changes that work together:

### Change 1: Make Mandatory Review Optional Per Technician

Add a setting on each technician's profile that controls whether their cases require senior review before being sent out.

**How it works:**

- By default, all Level 1 technicians still require review (nothing changes for new hires)
- An administrator can turn off mandatory review for a specific technician when they're ready
- When turned off, that technician can send cases out directly — just like a Level 2 or Level 3 tech
- The technician stays classified as Level 1 (their level doesn't change)
- This setting can be turned back on at any time

**Example:** Chris turns off mandatory review for Ileana. Ileana can now complete and send out cases on her own. She's still a Level 1 tech, but she's trusted to handle routine cases independently.

---

### Change 2: Allow Any Technician to Request Help on a Specific Case

Add a "Request Review" option that any technician can use when they want a senior person to look at a case before it goes out.

**How it works:**

- A new "Request Review" button appears alongside the existing "Mark as Completed" button
- When clicked, the technician writes a note explaining what help they need
- They can optionally choose who they want to review it (e.g., Ileana picks Tiffany, or Tiffany picks Chris)
- The selected reviewer gets a notification and sees the help request when they open the case
- The reviewer can then approve the case, make corrections, or send it back with feedback
- If no specific reviewer is chosen, all senior techs and administrators are notified

**Example 1:** Ileana is working a case and has a question about the FERS calculation. She clicks "Request Review," writes "Need help verifying the FERS supplement calculation — the dates seem off," and selects Tiffany. Tiffany gets a notification, reviews the case, and either approves it or sends feedback.

**Example 2:** Tiffany is working a complex case and wants Chris's input. She clicks "Request Review," writes her notes, and selects Chris. Same process.

---

## What This Means Day-to-Day

| Scenario | Before | After |
|----------|--------|-------|
| Ileana finishes a routine case | Must wait for Tiffany to review before it goes out | Can send it out directly |
| Ileana has a question on a case | No formal way to ask for help — has to message Tiffany separately | Clicks "Request Review," writes what she needs, Tiffany is notified |
| Tiffany needs Chris's input | No formal way to route a case to Chris | Clicks "Request Review," writes what she needs, Chris is notified |
| A new Level 1 tech is hired | All cases require review | All cases still require review (default behavior unchanged) |

---

## Who Controls What

| Action | Who Can Do It |
|--------|--------------|
| Turn mandatory review on/off for a technician | Administrators only |
| Request a review on a specific case | Any technician |
| Approve or respond to a review request | Level 3 technicians and administrators |

---

## Summary

These two changes give you the flexibility to:

- **Stop** Tiffany from having to review every one of Ileana's cases
- **Keep** the safety net so Ileana can ask for help when she needs it
- **Allow** Tiffany to escalate cases to Chris when needed
- **Maintain** mandatory review for any new or less experienced technicians
