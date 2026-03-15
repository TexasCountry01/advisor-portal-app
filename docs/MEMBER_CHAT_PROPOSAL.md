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

## Urgent Messages

- Member toggles "Urgent" when creating a question (or during a conversation)
- Urgent messages show a **red badge** in the staff queue
- Staff receives an **in-app notification** plus an **email alert** for urgent items

---

## Notifications

| Event | What Happens |
|---|---|
| Member sends a new question | Staff gets in-app notification |
| Member sends an **urgent** question | Staff gets in-app notification **+ email** |
| Staff replies | Member sees unread badge on "Messages" |
| Broadcast sent | Appears in every member's Messages list |

---

## Build Phases

- **Phase 1:** Members can submit questions · Staff can see the queue and reply
- **Phase 2:** Full chat view · Notifications · Urgent email alerts
- **Phase 3:** User directory · Broadcast · Retire "Beta Feedback" button

---

## What It Doesn't Change

- Existing **case chat** stays exactly as it is — no changes
- Existing **case workflow** is untouched
- This is a **completely separate system** alongside the current case features
