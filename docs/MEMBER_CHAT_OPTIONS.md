# Member Chat & Messaging System — Options

**Date:** March 15, 2026

## The Request (Combined)

This combines the "General Questions" and "Panic Button / Urgent Contact" features into a single unified messaging system. The user's requirements:

1. **Member side:** A chat feature on the dashboard where members can ask general (non-case) questions, see the back-and-forth conversation, and mark a question as urgent.
2. **Tech side:** A separate queue (apart from the cases queue) where staff can see a list of all users, view full chat history per user, and receive notifications when new chats arrive. Only non-case questions appear here — case-specific chat stays on the case.
3. **Broadcast:** Tech/Manager/Admin can send a blanket message to all members (announcement / broadcast functionality).

---

## Current State

| What Exists Today | Details |
|---|---|
| **Case Chat** | `CaseMessage` model — two-way messaging between member and tech, tied to a specific case. Shown in a tab on the case detail page. Tracks read/unread via `UnreadMessage` model. |
| **In-App Notifications** | `CaseNotification` (members) and `StaffNotification` (staff). Members see a bell icon with unread badge; staff see notifications on their dashboard. |
| **Email Alerts** | `email_service.py` sends emails for case completion, tech comments, and hold notifications. Global kill switch via `SystemSettings.email_notifications_enabled`. Member + delegates receive emails via `get_case_recipient_emails()`. |
| **Beta Feedback** | `BetaFeedback` model in `core/models.py` — freeform text submissions from members. Triggers `#betaFeedbackModal` from the nav bar. Will eventually be removed. |
| **No real-time push** | No WebSockets, Django Channels, or Celery. All interactions are standard HTTP + AJAX polling. |
| **No standalone messaging** | All communication requires an existing case. There is no way to message staff without creating a case first. |

---

## Option 1: New "Conversations" System (Standalone Models)

Build a purpose-built messaging system separate from the case infrastructure.

### New Models

```
Conversation
├── id, member (FK → User), subject, is_urgent (bool), status (open/closed)
├── created_at, updated_at, closed_at
├── assigned_to (FK → User, nullable) — tech who claims it
└── is_broadcast (bool) — True for announcements

ConversationMessage
├── id, conversation (FK), author (FK → User), message (text)
├── created_at
└── (ordering: chronological)

ConversationUnread
├── id, conversation (FK), user (FK → User), created_at
└── (deleted when user views the conversation — same pattern as UnreadMessage)
```

### Member Experience

- **Nav bar:** Replace "Beta Feedback" with **"Messages"** (with unread badge)
- **Dashboard:** New card below the cases table: "My Messages" — shows open conversations with latest message preview, unread indicator, and a "New Question" button
- **Conversation view:** Full chat-style page showing the back-and-forth thread with the tech. Member can mark as urgent when creating or during the conversation.
- **Broadcasts:** Appear in the Messages list (read-only, from "Benefits Team")

### Tech/Admin/Manager Experience

- **Nav bar:** New **"Messages"** link (with unread count badge)
- **Messages page:** Three tabs:
  - **Open Questions** — Queue of unclaimed/active conversations (filterable by urgent, assigned, unassigned)
  - **All Users** — Alphabetical list of all members; click to see full conversation history with that member
  - **Broadcasts** — Create and view past broadcast announcements
- **Conversation view:** Same chat-style page; tech can reply, close, or reassign
- **Notifications:** `StaffNotification` created when a new conversation arrives; email alert for urgent

### Broadcast Flow

- Staff clicks "New Broadcast" → enters subject + message
- System creates one `Conversation` per active member (with `is_broadcast=True`)
- Members see it in their Messages list; no reply needed (or optionally allow replies)
- **Alternative:** Single broadcast record + per-user read tracking (lighter weight)

| Pros | Cons |
|---|---|
| Clean separation from cases — no confusion | Most development work (~3-4 days) |
| Purpose-built chat UI with full history per user | New URL routes, templates, views, models |
| Broadcast is a natural extension | Staff must monitor a second queue |
| Urgent flag is built in from the start | |
| Replaces Beta Feedback slot cleanly | |

---

## Option 2: Extend Case Chat to Support "No-Case" Threads

Reuse the existing `CaseMessage` and `UnreadMessage` infrastructure by allowing conversations that aren't attached to a case.

### Model Changes

```
CaseMessage (existing — add fields):
├── conversation_type: 'case' | 'general' | 'broadcast'  (default: 'case')
├── subject: CharField (nullable — for general questions)
├── is_urgent: BooleanField (default: False)
├── thread_id: UUID (groups messages into a conversation when case is null)
├── case: FK (NOW NULLABLE — null for general questions)

New: GeneralThread
├── id (UUID), member (FK), subject, is_urgent, status, assigned_to
├── created_at, closed_at
└── messages → CaseMessage via thread_id
```

### Member Experience

- Same as Option 1 from the member's perspective
- Messages list on dashboard pulls from both case messages (existing) and general threads (new)

### Tech/Admin/Manager Experience

- "General Questions" tab on existing dashboard OR separate Messages page
- Reuses the same message display code as case chat

### Broadcast Flow

- Create a `GeneralThread` per member with `conversation_type='broadcast'`

| Pros | Cons |
|---|---|
| Reuses existing message/unread infrastructure | Muddies the CaseMessage model — it now serves two purposes |
| Less new code — adapts existing views | Nullable `case` FK adds complexity to every existing query |
| Familiar UI for both members and techs | Broadcast at scale could create many records |
| | Risk of bugs in existing case chat from the schema change |

---

## Option 3: Lightweight "Help Desk" Queue (Recommended)

Build a focused, independent messaging system — but keep it simple. No heavy ticketing, no categories. Think of it as "text messaging between members and the benefits team."

### New Models

```
MessageThread
├── id, member (FK → User), subject (CharField, 200)
├── is_urgent (BooleanField, default=False)
├── status: 'open' | 'closed' (default: 'open')
├── assigned_to (FK → User, nullable) — staff who claims it
├── thread_type: 'question' | 'broadcast' (default: 'question')
├── created_at, updated_at, closed_at
└── Indexes: [member, status], [assigned_to, status], [thread_type, status]

DirectMessage
├── id, thread (FK → MessageThread), author (FK → User)
├── message (TextField)
├── created_at
└── Indexes: [thread, created_at]

MessageReadStatus
├── id, thread (FK → MessageThread), user (FK → User)
├── last_read_at (DateTimeField)
└── (Unread = messages.created_at > last_read_at; no delete-on-read needed)
```

### Member Experience

**Nav bar changes:**
- Replace "Beta Feedback" with **"Messages"** — includes unread count badge
- Clicking opens a Messages page (not a modal)

**Messages page:**
- Clean list of all conversations (newest first)
- Each row: subject, last message preview, timestamp, urgent badge, unread dot
- **"New Question"** button at top → form with Subject + Message + Urgent checkbox
- Broadcasts from staff appear here too (labeled "From Benefits Team")

**Conversation view:**
- Simple chat-style layout — messages in bubbles, member on right, staff on left
- Text input at bottom to reply
- Urgent toggle visible (can escalate an existing thread)

**Dashboard integration:**
- Small card on the member dashboard: "You have X unread messages" with a link to the Messages page
- Or: unread badge on the nav bar is sufficient (no dashboard card needed)

### Tech/Admin/Manager Experience

**Nav bar:**
- New **"Messages"** link with unread count badge (between Dashboard and All Cases)

**Messages Queue page (/messages/):**
- **Stats row:** Total Open | Urgent | Unassigned | My Threads
- **Filter bar:** Status (Open/Closed) | Urgent Only | Assigned To | Search
- **Thread list table:** Member Name | Subject | Last Message | Urgent | Assigned To | Last Activity
- Click a row → conversation view (same chat-style as member, but with staff controls)

**Conversation view (staff):**
- Same chat bubbles as member view
- Additional controls: Assign to Me | Close Thread | Mark Urgent/Normal
- Full history preserved — staff sees every past message in the thread

**User Directory (/messages/users/):**
- Alphabetical list of all members
- Shows: member name, total threads, open threads, last activity
- Click a member → see all threads with that member (both open and closed)

**Broadcast (/messages/broadcast/):**
- "New Broadcast" button → Subject + Message form
- Creates a single `MessageThread` with `thread_type='broadcast'`
- All members see it in their Messages list
- Read tracking via `MessageReadStatus` — staff can see who has/hasn't read it
- Members can optionally reply (creates a new regular thread referencing the broadcast)

### Technical Implementation

**New app:** `messaging/` (keeps it cleanly separated from `cases/`)

```
messaging/
├── models.py          (MessageThread, DirectMessage, MessageReadStatus)
├── views.py           (thread list, conversation, broadcast, user directory)
├── urls.py            (message routes)
├── admin.py           (MessageThread + DirectMessage admin)
├── templates/
│   └── messaging/
│       ├── thread_list.html        (member's Messages page)
│       ├── staff_queue.html        (staff queue page)
│       ├── conversation.html       (shared chat view)
│       ├── user_directory.html     (staff: all-users list)
│       └── broadcast_form.html     (staff: create broadcast)
└── services/
    └── notification_service.py     (email + in-app alerts for new messages)
```

**Integration points:**
- `base.html` nav bar: Replace "Beta Feedback" with "Messages" + badge
- `StaffNotification`: Create notification when member sends a new message
- `email_service.py`: Add `send_new_message_alert()` for urgent threads
- Dashboard views: Add unread message count to context (optional dashboard card)

### Notification Flow

| Event | In-App | Email |
|---|---|---|
| Member sends new question | `StaffNotification` to assigned tech (or all techs if unassigned) | Only if marked Urgent |
| Staff replies | In-app badge update for member | Optional (configurable) |
| Member sends urgent message | `StaffNotification` (flagged urgent) | Yes — immediate email to tech team |
| New broadcast sent | Appears in member's Messages list | Optional bulk email |
| Thread closed | In-app notification to member | No |

| Pros | Cons |
|---|---|
| Clean separation — own app, own models, no risk to existing case chat | More new code than Option 2 (~2-3 days) |
| Simple "text message" UX — no overengineering | Staff has a second queue to monitor |
| Broadcast is a natural thread type, not a bolt-on | No real-time push (same as case chat — AJAX refresh) |
| Urgent flag built in at the thread level | |
| User directory gives staff the "see all users" view requested | |
| `MessageReadStatus` with `last_read_at` is more efficient than per-message unread records | |
| Replaces Beta Feedback cleanly | |
| No changes to existing case models or queries | |

---

## Option 4: Minimal "Ask a Question" + Broadcast (Fastest Path)

Skip building a full chat UI. Instead, create a simple question submission flow and a broadcast system.

### Member Experience

- "Ask a Question" button on dashboard → modal with Subject + Message + Urgent toggle
- Questions appear in a simple list on a "My Questions" page (no real-time chat)
- Staff replies show beneath the question (accordion-style, not chat bubbles)
- Broadcasts appear as alert banners on the dashboard

### Tech Experience

- "Questions" tab on existing dashboard
- Simple table: Member | Subject | Urgent | Status | Date
- Click to view question + reply (single reply, not threaded chat)
- Broadcast: "Send Announcement" from a management dropdown

| Pros | Cons |
|---|---|
| Fastest to build (~1 day) | Not a real chat — single question + single reply |
| Minimal UI changes | No conversation history per user |
| Broadcasts as dashboard banners are simple | Doesn't match the "back-and-forth" requirement |
| | Would need to be rebuilt if chat is wanted later |

---

## Comparison

| Criteria | Option 1 | Option 2 | Option 3 | Option 4 |
|---|---|---|---|---|
| **Matches "chat back-and-forth" requirement** | ✅ Full | ✅ Full | ✅ Full | ❌ Single reply |
| **Separate queue for staff** | ✅ Yes | ⚠️ Partial (tab on same dashboard) | ✅ Yes | ⚠️ Tab only |
| **Full user history view** | ✅ Yes | ⚠️ Possible but complex | ✅ Yes | ❌ No |
| **Broadcast to all members** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes (banners) |
| **Urgent flag** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Risk to existing case system** | ✅ None | ⚠️ Schema changes | ✅ None | ✅ None |
| **Development effort** | High (3-4 days) | Medium (2-3 days) | Medium (2-3 days) | Low (1 day) |
| **Replaces Beta Feedback** | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Partially |
| **Scalable for future needs** | ✅ Yes | ⚠️ Moderate | ✅ Yes | ❌ Limited |

---

## Recommendation

**Option 3 (Lightweight Help Desk Queue)** is the best fit. It delivers everything the user asked for — back-and-forth chat, separate staff queue, user directory with full history, urgent flagging, and broadcast — without overengineering or touching existing case infrastructure.

It's the same development effort as Option 2 but without the risk of breaking existing case chat, and it's significantly more complete than Option 4.

### Suggested Build Order

1. **Phase 1:** Models + migrations + member "New Question" flow + staff queue page
2. **Phase 2:** Conversation view (chat UI) + reply flow + notifications
3. **Phase 3:** User directory + broadcast + replace Beta Feedback in nav
