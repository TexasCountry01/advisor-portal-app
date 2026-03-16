# Messaging System — Phase 1 Implementation

**Date:** March 15, 2026  
**Status:** Implemented locally, not yet deployed  
**Reference:** [MEMBER_CHAT_PROPOSAL.md](MEMBER_CHAT_PROPOSAL.md)

---

## Overview

Phase 1 of the general messaging system allows members to submit non-case-related questions directly to staff through a dedicated "Messages" area. This is completely separate from the existing case chat system — general questions live in Messages, case conversations stay on the case.

### What Phase 1 Delivers

- Members can **ask general questions** with a subject and message body
- Members can **mark a question as urgent**
- Staff (technicians, administrators, managers) see a **message queue** with all member questions
- Staff can **filter** by status (open/closed), assignment (all/mine/unassigned), and urgency
- Staff can **claim/take over**, **reply**, **close**, and **reopen** conversations
- Full **back-and-forth chat** within each conversation thread
- **Unread message badge** on the "Messages" nav link (all roles)
- **30-second auto-refresh polling** to keep the badge count current

### What Phase 1 Does NOT Include (Future Phases)

- Urgent email alerts to staff (Phase 2)
- Urgent badge on case queue for case chats (Phase 2)
- User directory for staff (Phase 3)
- Broadcast announcements (Phase 3)
- Retiring the Beta Feedback button (Phase 3)

---

## New Django App: `messaging`

A new standalone Django app was created at `messaging/` with its own models, views, URLs, templates, and admin config.

### Files Created

| File | Purpose |
|------|---------|
| `messaging/models.py` | 3 data models (Conversation, Message, MessageReadStatus) |
| `messaging/views.py` | 8 view functions (inbox, detail, new, reply, claim, close, reopen, unread API) |
| `messaging/urls.py` | 8 URL patterns under `/messages/` |
| `messaging/admin.py` | Django admin registration with inlines and filters |
| `messaging/migrations/0001_initial.py` | Auto-generated migration (3 models, 7 indexes) |
| `messaging/templates/messaging/inbox.html` | Message inbox / queue page |
| `messaging/templates/messaging/conversation_detail.html` | Conversation thread view with chat bubbles |
| `messaging/templates/messaging/new_conversation.html` | New question submission form |

### Files Modified

| File | Change |
|------|--------|
| `config/settings.py` | Added `'messaging'` to `INSTALLED_APPS` |
| `config/urls.py` | Added `path('messages/', include('messaging.urls', namespace='messaging'))` |
| `templates/base.html` | Added "Messages" nav link with unread badge for all 3 roles + 30-second polling JS |

---

## Data Models

### Conversation

The top-level thread representing a member's general question.

| Field | Type | Description |
|-------|------|-------------|
| `subject` | CharField(255) | Question subject line |
| `started_by` | FK → User | Member who created the conversation |
| `is_urgent` | BooleanField | Whether the question is marked urgent |
| `status` | CharField (`open`/`closed`) | Conversation status, default `open` |
| `assigned_to` | FK → User (nullable) | Staff member who claimed this conversation |
| `created_at` | DateTimeField (auto) | When the conversation was created |
| `updated_at` | DateTimeField (auto) | Last activity timestamp |
| `closed_at` | DateTimeField (nullable) | When conversation was closed |
| `closed_by` | FK → User (nullable) | Staff member who closed it |

**Indexes:** `(started_by, -updated_at)`, `(status, -updated_at)`, `(assigned_to, status)`

### Message

An individual message within a conversation.

| Field | Type | Description |
|-------|------|-------------|
| `conversation` | FK → Conversation | Parent conversation |
| `author` | FK → User | Who wrote this message |
| `body` | TextField | Message content |
| `created_at` | DateTimeField (auto) | When the message was sent |

**Index:** `(conversation, created_at)`

### MessageReadStatus

Tracks unread messages per user. Uses the **"record exists = unread"** pattern (same as `cases.UnreadMessage`). When a user views a conversation, all their `MessageReadStatus` records for that conversation are deleted.

| Field | Type | Description |
|-------|------|-------------|
| `message` | FK → Message | The unread message |
| `user` | FK → User | The user who hasn't read it yet |
| `conversation` | FK → Conversation | Denormalized for efficient badge queries |
| `created_at` | DateTimeField (auto) | When the unread record was created |

---

## URL Routes

All routes are under `/messages/` with namespace `messaging`.

| URL | Name | Method | Description |
|-----|------|--------|-------------|
| `/messages/` | `inbox` | GET | Message inbox (member: own conversations, staff: all) |
| `/messages/new/` | `new_conversation` | GET/POST | Member creates a new question |
| `/messages/<id>/` | `conversation_detail` | GET | View conversation thread |
| `/messages/<id>/reply/` | `reply` | POST | Add a reply to a conversation |
| `/messages/<id>/claim/` | `claim` | POST | Staff claims/reassigns conversation to self |
| `/messages/<id>/close/` | `close` | POST | Staff closes the conversation |
| `/messages/<id>/reopen/` | `reopen` | POST | Staff reopens a closed conversation |
| `/messages/unread-count/` | `unread_count` | GET | API: returns `{ "count": N }` for nav badge |

---

## View Logic

### `inbox` (GET)

- **Members:** See only their own conversations, ordered by most recent activity. Optional status filter (open/closed).
- **Staff:** See all conversations with filter controls:
  - Status: Open (default), Closed, All
  - Assigned: All, Mine, Unassigned
  - Urgent only checkbox
- Each conversation in the list shows: subject, urgent badge, unread count badge, latest message preview (truncated to 120 chars), time since last update, open/closed status, and (staff only) assigned-to name and who started the conversation.

### `conversation_detail` (GET)

- Displays the full message thread in **chat-bubble style**:
  - Current user's messages: blue bubbles, right-aligned
  - Member messages (from others): light background, left-aligned
  - Staff messages (from others): green-tinted, left-aligned
- **Marks all messages as read** for the current user on load (deletes `MessageReadStatus` records)
- Staff action buttons: Claim / Take Over / Close / Reopen
- Reply form at the bottom
- Auto-scrolls to the bottom of the thread on page load

### `new_conversation` (GET/POST)

- Form with: Subject (text), Message body (textarea), Urgent checkbox
- On submit: Creates a `Conversation` + the first `Message` + `MessageReadStatus` records for all active staff
- Redirects to the new conversation's detail page

### `reply` (POST)

- Creates a new `Message` in the conversation
- Updates `conversation.updated_at` (auto_now)
- If the conversation was closed, **automatically reopens it**
- Creates `MessageReadStatus` for recipients:
  - Staff reply → unread for the member who started the conversation
  - Member reply → unread for all active staff (bulk create)

### `claim_conversation` (POST, staff only)

- Sets `assigned_to` to the requesting staff user
- Works for both unclaimed conversations and reassignment (Take Over)

### `close_conversation` (POST, staff only)

- Sets `status='closed'`, records `closed_at` and `closed_by`

### `reopen_conversation` (POST, staff only)

- Sets `status='open'`, clears `closed_at` and `closed_by`

### `unread_count` (GET, API)

- Returns JSON `{ "count": N }` where N is the number of **distinct conversations** with unread messages for the current user
- Used by the nav badge polling script

---

## Navigation Integration

The "Messages" link was added to the **top navigation bar** in `base.html` for all three roles:

- **Member:** Appears after "Beta Feedback"
- **Technician:** Appears after "All Cases"
- **Administrator:** Appears after "All Cases"

Each link includes:
- Envelope icon (`bi-envelope`)
- "Messages" text
- Red pill badge (`#nav-messages-badge`) that shows the count of conversations with unread messages

### Badge Polling

A JavaScript function `refreshMessagesBadge()` runs inside the `{% if user.is_authenticated %}` block at the bottom of `base.html`:

1. Fetches `/messages/unread-count/` via `fetch()` API
2. If count > 0: shows the badge with the count
3. If count = 0: hides the badge
4. Runs immediately on page load, then every **30 seconds** via `setInterval`

---

## Permission Model

| Action | Member | Technician | Administrator | Manager |
|--------|--------|------------|---------------|---------|
| View inbox | Own conversations only | All conversations | All conversations | All conversations |
| Create new question | ✅ | ❌ (no "New Question" button) | ❌ | ❌ |
| View conversation | Own only | All | All | All |
| Reply | Own only | All | All | All |
| Claim / Take Over | ❌ | ✅ | ✅ | ✅ |
| Close | ❌ | ✅ | ✅ | ✅ |
| Reopen | ❌ | ✅ | ✅ | ✅ |

Staff roles are defined as: `STAFF_ROLES = ('technician', 'administrator', 'manager')`

---

## Admin Interface

All three models are registered in Django admin:

- **ConversationAdmin:** List display (subject, started_by, urgent, status, assigned_to, dates), filters (status, urgent, created_at), search (subject, username, name), inline Message display
- **MessageAdmin:** List display (conversation, author, created_at), date filter, raw_id_fields
- **MessageReadStatusAdmin:** List display (user, conversation, message, created_at), date filter, raw_id_fields

---

## Relationship to Existing Systems

### Separate from Case Chat

The messaging system is **completely independent** from the case-based chat (case comments / `CaseMessage` model). They share no models, no views, and no templates.

| System | What It's For | Where It Lives |
|--------|---------------|----------------|
| Case Chat | Discussion about a specific case | Case detail page → Chat tab |
| General Messages | Non-case questions to staff | `/messages/` (new) |
| Case Notifications (bell) | Case activity alerts | Notification bell in nav |
| Message Badge | Unread general question count | "Messages" link in nav |

### Beta Feedback Still Active

The existing Beta Feedback functionality (modal + report) is **still in place** and fully operational. It has not been removed or replaced. Per the proposal, retiring Beta Feedback is planned for Phase 3.

| Beta Feedback Component | Status |
|--------------------------|--------|
| "Beta Feedback" nav link (member) | ✅ Still active |
| Beta Feedback modal in `base.html` | ✅ Still active |
| `core.BetaFeedback` model | ✅ Still active |
| `core/views.py → submit_beta_feedback()` | ✅ Still active |
| `core/views_reports.py → beta_feedback_report()` | ✅ Still active |
| `/beta-feedback/` submission URL | ✅ Still active |
| `/reports/beta-feedback/` report URL | ✅ Still active |

---

## Deployment Notes

### Migration Required

```bash
python manage.py migrate messaging
```

This creates 3 tables: `messaging_conversation`, `messaging_message`, `messaging_messagereadstatus` with 7 database indexes.

### No Data Migration Needed

This is a net-new app. No existing data needs to be migrated or transformed.

### Server Restart Required

Gunicorn/Django must be restarted to pick up the new app, URL routes, and templates.
