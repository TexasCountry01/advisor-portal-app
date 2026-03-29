# Pending Changes — Awaiting Approval for Production

**Date:** March 21, 2026  
**Status:** Deployed to TEST server — awaiting approval for Production  
**TEST URL:** https://test.profeds.com (or applicable TEST URL)

---

## Summary

There is **one new feature** waiting to go live: a **Messages** area in the portal. Everything else (bug fixes, email fixes, scheduled release timing) has already been deployed to Production.

---

## New Feature: Messages

### What It Does

A new **"Messages"** section has been added to the portal that gives members a way to ask general questions directly to staff — without needing to have an open case. Think of it as an "Ask Us Anything" inbox.

### How It Works for Members

- A new **"Messages"** link appears in the navigation bar at the top of the portal
- Members click **"New Question"** to submit a question with a subject line
- If it's time-sensitive, they can check **"Urgent"**
- When staff replies, a **red notification badge** appears on the Messages link
- Members can click into any conversation to see the full thread and reply back

### How It Works for Staff

- Staff see a **Message Queue** showing all incoming member questions
- Staff can filter by: Open/Closed, Assigned to Me, Unassigned, and Urgent
- Staff can **Claim** a question to assign it to themselves
- Staff can **Reply**, **Close** (when resolved), or **Reopen** a conversation
- If a member replies to a closed conversation, it automatically reopens

### What This Does NOT Change

- **Case workflows** — Everything about how cases are submitted, assigned, reviewed, and released stays exactly the same
- **Case chat** — The chat/discussion on individual case pages is unchanged
- **Dashboards** — All existing dashboards remain the same
- **Email notifications** — No changes to how email alerts work
- **Beta Feedback** — Still available, no changes

### Why This Feature Was Requested

Members currently have no way to ask general questions (e.g., "When is the next enrollment window?" or "Can you help me understand my benefit options?") without submitting a formal case. This feature fills that gap.

---

## Bug Fixes Already Deployed to Production

The following items were completed and are **already live** — no approval needed:

1. **Email timing fix** — Scheduled release emails now go out at the specific time chosen by the technician, instead of all releasing at midnight
2. **Email reliability fix** — Notification emails are now tracked accurately; if an email fails to send, the system automatically retries on the next cycle
3. **Email password update** — The system email account credentials were refreshed after an expiration

---

## What Happens Next

1. **You review and test** the Messages feature on the TEST server
2. **Let us know** if anything needs to be adjusted
3. Once approved, we deploy to Production — the feature goes live for all users immediately
