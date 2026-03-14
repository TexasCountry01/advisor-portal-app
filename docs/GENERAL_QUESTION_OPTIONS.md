# General Question Feature — Options

**Date:** March 14, 2026

## The Request

Members want to submit general questions (not specific to a particular case) directly from their main dashboard. Technicians should be notified when a question comes in.

## Current State

Today, the entire portal is **case-centric** — all communication (messages, notes, questions) is tied to a specific case. Members cannot ask questions without first creating a case. There is no separate queue for general questions.

---

## Option 1: Standalone General Question Model (Separate Queue)

Create a brand-new **General Question** system independent of cases. Technicians get a dedicated "Questions" tab on their dashboard.

| Aspect | Details |
|--------|---------|
| **Member experience** | "Ask a Question" button on dashboard → simple form (subject + message) |
| **Technician experience** | New "General Questions" section on dashboard with unread count, claim/reply/close actions |
| **Notifications** | Email alert to technicians when a question is submitted |
| **Pros** | Clean separation from cases; purpose-built for Q&A |
| **Cons** | Most development work — new data model, pages, notifications, and admin views |

---

## Option 2: Lightweight Case Variant (Reuse Existing System)

Add a "General Inquiry" flag to the existing case system. Members submit a simplified form, and it flows through the same dashboard technicians already use.

| Aspect | Details |
|--------|---------|
| **Member experience** | "Ask a Question" button on dashboard → simplified form (just subject + message — no employee info, no Fact Finder, no reports) |
| **Technician experience** | Questions appear on existing dashboard with a filter to toggle between "Cases" and "Questions" |
| **Notifications** | Reuses existing notification and email system |
| **Pros** | Leverages all existing infrastructure (assignment, messaging, notifications, audit trail); least new code |
| **Cons** | Questions live alongside cases — dashboard stat cards and filters need adjustments to separate them |

---

## Option 3: Embedded Quick Question Widget (No Queue)

Add a simple "Quick Question" form directly on the member dashboard. No formal queue — questions are delivered via email notification to the tech team.

| Aspect | Details |
|--------|---------|
| **Member experience** | Collapsible form right on the dashboard → type question → submit |
| **Technician experience** | Receives email notification with question text; replies via email or a simple list page |
| **Notifications** | Immediate email to tech team |
| **Pros** | Fastest to build; minimal complexity; feels lightweight to the member |
| **Cons** | No formal tracking or queue; questions could get lost; no assignment or ownership |

---

## Option 4: Full Ticketing / Inquiry System

Build a proper ticket system alongside cases — its own queue, assignment workflow, status lifecycle (Open → Assigned → Answered → Closed), and optional categories.

| Aspect | Details |
|--------|---------|
| **Member experience** | "Submit a Question" → form with optional category (billing, general, technical, etc.) |
| **Technician experience** | Separate "Inquiries" page with filters, assignment, and status tracking |
| **Notifications** | Full notification chain (new inquiry, response received, resolved) |
| **Pros** | Most robust; supports categorization and reporting; scalable |
| **Cons** | Heaviest development lift; essentially a mini help-desk inside the portal |

---

## Option 5: Standalone Message Threads (No Case Required)

Extend the existing messaging system to support conversations not attached to a case. Members start a thread, technicians reply within it.

| Aspect | Details |
|--------|---------|
| **Member experience** | "New Question" button → starts a message thread visible on dashboard |
| **Technician experience** | "Open Questions" section on dashboard showing unattached threads |
| **Notifications** | Reuses existing unread message tracking + email alerts |
| **Pros** | Familiar message interface; reuses existing unread tracking; moderate effort |
| **Cons** | Messaging system wasn't designed for standalone use; may need some refactoring |

---

## Comparison Summary

| Criteria | Option 1 | Option 2 | Option 3 | Option 4 | Option 5 |
|----------|----------|----------|----------|----------|----------|
| **Development effort** | High | Low | Lowest | Highest | Medium |
| **Formal queue / tracking** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| **Tech notified** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Reuses existing system** | ❌ No | ✅ Yes | Partially | ❌ No | Partially |
| **Separate from cases** | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Supports assignment** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| **Scalable if volume grows** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ⚠️ Moderate |

---

## Recommendation

**Option 2** offers the best balance of functionality and efficiency. It reuses the existing dashboard, notifications, assignment, audit trail, and messaging — meaning members and technicians work in a system they already know. If question volume grows later, it's straightforward to split questions into their own dedicated tab.

**To answer the original question directly:** No, there is not currently a separate queue for questions. All of these options would create one (except Option 3, which is notification-only).
