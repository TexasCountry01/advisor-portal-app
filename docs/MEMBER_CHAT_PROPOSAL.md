# Member Messaging & Chat — Proposal

## What This Solves

Today, all communication in the portal is tied to a specific case. There's no way for a member to ask a general question, flag something as urgent, or receive announcements without having a case open. This new messaging system fills that gap.

---

## What It Does

- Members can **ask general questions** without needing a case
- Members can **mark a question as urgent** to alert the team immediately
- Techs get a **separate message queue** (apart from the cases queue) for these questions
- Techs can **view a list of all members** and see full conversation history with each one
- Techs/Managers/Admins can **broadcast announcements** to all members
- All conversations are **back-and-forth chat style** — not one-and-done

---

## Member Experience

- **"Messages"** replaces "Beta Feedback" in the top navigation bar
  - Shows an unread count badge when new replies arrive
- Click it → see a list of all your conversations
- **"New Question"** button → enter a subject, type your message, toggle Urgent if needed
- Click any conversation → full chat view showing the back-and-forth with the tech
- Broadcast announcements from staff also appear in this list

---

## Tech / Admin / Manager Experience

- **"Messages"** link added to the top navigation bar (with unread count badge)

- **Message Queue** — all open questions from members
  - Filter by: Urgent · Assigned to Me · Unassigned · Open/Closed
  - Claim a question · Reply · Close when resolved

- **User Directory** — alphabetical list of all members
  - Click any member → see every conversation (open and closed) with that person

- **Broadcast** — send an announcement to all members at once
  - Track who has read it

---

## Two Separate Systems — How They Work Together

The tech's top navigation bar will have **two indicators** with their own red bubble badges:

1. **Notifications** (bell icon) — for case-related activity (same as today)
2. **Messages** — for general questions from members (new)

These two systems **never cross**. Case chat stays in Notifications. General questions stay in Messages.

---

## Case Chat (Existing System — Small Enhancement)

This is the chat that already exists on each case. It stays exactly where it is.

| Scenario | Where Tech Sees It | What Happens |
|---|---|---|
| Member sends a **normal** case chat | **Notifications** bell only | Same as today — notification appears under the bell |
| Member sends an **URGENT** case chat | **Notifications** bell | Notification appears under the bell **+ the case row in the tech's case queue gets an URGENT badge** so it stands out from regular comments |

- The URGENT badge makes it visually obvious in the case queue — it's not just another comment
- Case chat does **not** appear in the new Messages area — it stays tied to the case

---

## General Messages (New System)

This is the new system for non-case questions. Completely separate from cases.

| Scenario | Where Tech Sees It | What Happens |
|---|---|---|
| Member sends a **normal** general question | **Messages** area | Appears in the message queue · Unread badge on "Messages" in nav |
| Member sends an **URGENT** general question | **Messages** area | Appears in the message queue with **red URGENT badge** · Unread badge on "Messages" in nav · **Email alert** sent to staff |

- General messages do **not** appear in the Notifications bell — they have their own dedicated area
- All general questions (urgent or not) live in the Messages queue

---

## What the Tech Nav Bar Looks Like

```
Dashboard · All Cases · Messages (3) · Notifications (5) · Profile · Logout
```

- **Messages (3)** — 3 unread general questions from members
- **Notifications (5)** — 5 case-related notifications (comments, uploads, status changes)
- Each has its own independent red bubble count

---

## Summary: Where Does Each Thing Go?

| What the Member Does | Where the Tech Sees It |
|---|---|
| Sends a case chat (normal) | 🔔 Notifications |
| Sends a case chat (URGENT) | 🔔 Notifications + URGENT badge on the case in the queue |
| Sends a general question (normal) | 💬 Messages |
| Sends a general question (URGENT) | 💬 Messages (with URGENT badge) + email alert |
| — | |
| Staff sends a broadcast | 💬 Appears in every member's Messages list |

---

## Build Phases

- **Phase 1:** Members can submit general questions · Staff can see the message queue and reply
- **Phase 2:** Full chat view · Notifications · Urgent email alerts · Urgent badge on case queue
- **Phase 3:** User directory · Broadcast · Retire "Beta Feedback" button

---

## What It Doesn't Change

- Existing **case chat** stays exactly as it is — lives on the case, shows in Notifications
- Existing **case workflow** is untouched
- The only addition to the case system is the **URGENT badge** on the case row in the queue
