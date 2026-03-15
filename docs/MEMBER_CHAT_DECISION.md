# Member Messaging & Chat — Decision Summary

## What You Asked For

- Members can **ask general questions** (not tied to a case) and see the **back-and-forth conversation**
- Members can **mark a question as urgent**
- Techs get a **separate queue** for these questions (apart from the cases queue)
- Techs can **see a list of all users** and view **full chat history** per user
- Techs are **notified** when a new chat arrives
- Techs/Managers/Admins can **send a broadcast message** to all members

---

## What Exists Today

- All messaging is **tied to a specific case** — no way to message without one
- "Beta Feedback" button in the nav bar will eventually be removed — that slot can be repurposed
- Case chat, notifications, and email alerts are all built and working

---

## Options

### Option A: Extend the Existing Case System

- General questions get shoehorned into the current case/message tables
- **Pros:** Less new code, reuses what's already built
- **Cons:** Risks breaking existing case chat; mixes two different things in one system; harder to maintain long-term

### Option B: New Standalone Messaging System *(Recommended)*

- Brand-new "Messages" section — completely separate from cases
- **Pros:** Clean separation, no risk to existing features, built for exactly what you described
- **Cons:** More new code to write (but not significantly more than Option A)

### Option C: Simple Question Form (No Real Chat)

- Members submit a question, staff sends one reply — not a real conversation
- **Pros:** Fastest to build
- **Cons:** Doesn't match your "back-and-forth" requirement; would need to be rebuilt later

---

## How Option B Would Work

### For Members

- **"Messages"** replaces "Beta Feedback" in the navigation bar (with unread count badge)
- Click it → see all your conversations in a list
- **"New Question"** button → enter a subject, type your message, toggle Urgent if needed
- Click into any conversation → see the full back-and-forth chat with the tech
- Broadcast announcements from staff also appear here

### For Techs / Admins / Managers

- **"Messages"** link added to the navigation bar (with unread count badge)
- Click it → **Message Queue** showing all open questions from members
  - Filter by: Urgent, Assigned to Me, Unassigned, Open/Closed
  - Claim a question, reply, close it when resolved
- **User Directory** tab → alphabetical list of all members
  - Click any member → see every conversation you've ever had with them
- **Broadcast** tab → send an announcement to all members at once

### Urgent Messages

- Member toggles "Urgent" when creating or during a conversation
- Staff sees urgent messages flagged with a red badge in the queue
- Urgent messages trigger an **immediate email alert** to the tech team

### Notifications

- New question from a member → staff gets an in-app notification
- Staff reply → member sees unread badge on "Messages" in the nav bar
- Urgent questions → in-app notification **plus** email to staff

---

## Build Phases

1. **Phase 1:** Member can submit a question, staff can see the queue and reply
2. **Phase 2:** Full chat view, notifications, urgent email alerts
3. **Phase 3:** User directory, broadcast, retire Beta Feedback button

---

## Recommendation

**Option B** — it delivers everything you described without touching the existing case system. Same effort as Option A but cleaner and safer.
