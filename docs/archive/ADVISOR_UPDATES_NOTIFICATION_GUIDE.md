# Post-Submission Member Updates & Notifications - Reference Guide

**Last Updated:** January 23, 2026  
**Purpose:** Quick reference for how members/advisors update cases after submission and how techs get notified

---

## 📋 Quick Reference

| Question | Answer | See Section |
|----------|--------|-------------|
| How does tech know member added info? | Yellow dashboard badge (currently) | [Today's System](#todays-system) |
| What info is tracked? | Documents, notes, timestamps, who did it | [Behind the Scenes](#behind-the-scenes) |
| What are my notification options? | 4 options from basic to advanced | [Notification Options](#notification-options) |
| What should I choose? | Option C (email + timestamp) recommended | [Recommendation](#recommendation) |
| How does it work now? | Member uploads → badge appears → tech checks manually | [Current Workflow](#current-workflow) |
| How should it work? | Member uploads → email sent → dashboard timestamp shows | [Proposed Workflow](#proposed-workflow) |

---

## Table of Contents
1. [Today's System](#todays-system)
2. [Behind the Scenes](#behind-the-scenes)
3. [Notification Options](#notification-options)
4. [Decision Matrix](#decision-matrix)
5. [Implementation Roadmap](#implementation-roadmap)
6. [FAQ](#faq)

---

## Today's System

### How Tech Finds Out (Currently)
1. **Dashboard Badge** - Yellow "🔔 New Info" badge appears next to the case
2. **That's It** - No email, no popup, no alert

### The Problem
- ❌ Tech has to actively log in and check dashboard to see the badge
- ❌ If tech is busy or out, they might miss updates  
- ❌ No way to know WHAT was added without clicking into the case
- ❌ Badge disappears automatically when viewed, could be missed

### Badge Details
- **Color:** Yellow/Warning
- **Icon:** Info circle (ⓘ)
- **Text:** "New Info"
- **Shows On:** Technician Dashboard, Manager Dashboard
- **Clears When:** Tech/manager views the case detail

### What Triggers the Badge
- Member uploads document
- Member adds comment/note
- Member provides any new information post-submission

---

## Behind the Scenes

### System Records
When an advisor/member updates a case after submission:

1. **`has_member_updates` Flag**
   - Set to `TRUE` when member adds anything
   - Used to trigger dashboard badge
   - Lives on Case model in database

2. **`member_last_update_date` Timestamp**
   - Records WHEN the member last updated
   - Format: `2026-01-23 14:30:45`
   - Allows "updated 2 hours ago" calculations

3. **Audit Log Entry**
   - Records WHAT was added (document name, size, type, notes)
   - Records WHO added it (member ID or advisor ID)
   - Records WHEN it happened (datetime)
   - Creates searchable history for compliance

### Reset Behavior
- Badge automatically disappears when tech/manager/admin views the case
- `has_member_updates` flag resets to `FALSE`
- Audit trail remains (permanent record)

### What's Allowed Post-Submission
**Members Can:**
- Upload supporting documents
- Add notes/comments
- Provide additional information

**Advisors/Techs Can:**
- Edit employee name
- Edit due date
- Reassign case to different tech
- Upload documents on behalf
- Add internal notes

**Cannot Be Done (By Design):**
- Member cannot edit due date (prevents scope creep)
- Cannot change case status directly
- Cannot delete documents (audit trail protection)

---

## Notification Options

### **Option A: Send Email to Tech** ⭐
**Triggered By:** Member updates → Email sent to assigned tech

**What Tech Receives:**
```
Subject: New information added to Case ABC123
Body:
  Member Jane Smith has added information to Case ABC123
  Document: W-4 Form (2 pages, 145 KB)
  Date: Jan 23, 2026 2:30 PM
  [View Case Button]
```

**Benefits:**
- ✅ Tech knows instantly
- ✅ Can respond immediately
- ✅ Works even if tech not logged in
- ✅ Creates email trail for compliance

**Drawbacks:**
- ❌ Could generate many emails if member uploads multiple times
- ❌ Emails must be properly formatted and sent

**Implementation Time:** 1 week

**Code Changes Needed:**
- `cases/signals.py` - Listen for member_document_uploaded event
- `cases/emails.py` - Create email template
- `cases/tasks.py` - Queue email to send

---

### **Option B: Dashboard Timestamp**
**Display:** "Updated: 2 hours ago" next to case on dashboard

**What Tech Sees:**
```
Case ABC123  | Jane Smith    | Updated: 2 hrs ago
```

**Benefits:**
- ✅ Quick visual scan of dashboard
- ✅ No emails (tech controls pace)
- ✅ See at a glance which cases are active

**Drawbacks:**
- ❌ Still requires tech to check dashboard
- ❌ If tech is out, won't know
- ❌ No active notification

**Implementation Time:** 3-4 days

**Code Changes Needed:**
- `cases/models.py` - Add display method for timestamp
- `technician_dashboard.html` - Add timestamp column
- `manager_dashboard.html` - Add timestamp column
- `cases/views.py` - Calculate time-ago string

---

### **Option C: Email + Timestamp** ⭐⭐ RECOMMENDED
**Combines:** Options A + B for redundancy

**What Happens:**
1. Member uploads docs
2. **Email sent immediately** to tech
3. **Dashboard updated** to show timestamp
4. Tech can respond via email OR click dashboard link

**Benefits:**
- ✅ Active notification (email) + passive indicator (timestamp)
- ✅ Multiple ways to discover updates
- ✅ No single point of failure
- ✅ Tech definitely won't miss it

**Drawbacks:**
- ❌ More emails to manage
- ❌ Requires email configuration to work properly

**Implementation Time:** 1-1.5 weeks

**Why This is Best:**
- Combines speed (email) with visibility (dashboard)
- Tech can choose how to respond (email reply or web interface)
- Scales well as case volume grows

---

### **Option D: In-App Notification Modal**
**Triggers:** When tech logs in or refreshes page

**What Tech Sees:**
```
┌─────────────────────────────────────┐
│ New Case Updates                    │
├─────────────────────────────────────┤
│ ⚠ Case ABC123: 2 new documents      │
│ ⚠ Case XYZ789: Member extended docs │
│ ⚠ Case DEF456: Due date approaching │
│                                     │
│     [View] [Dismiss] [Settings]     │
└─────────────────────────────────────┘
```

**Benefits:**
- ✅ Eye-catching, can't be missed
- ✅ Shows multiple cases at once
- ✅ Detailed info without email

**Drawbacks:**
- ❌ Requires building new notification system
- ❌ Could be annoying if appears too often
- ❌ More complex to implement

**Implementation Time:** 2-3 weeks

**When to Use:** If you want visually prominent notifications

---

## Decision Matrix

| Aspect | Option A (Email) | Option B (Timestamp) | Option C (Both) | Option D (Modal) |
|--------|------------------|----------------------|-----------------|-----------------|
| **Tech Responsiveness** | ⭐⭐⭐⭐⭐ Instant | ⭐⭐ When checked | ⭐⭐⭐⭐⭐ Instant | ⭐⭐⭐⭐ On login |
| **Risk of Missing** | Very Low | High | Very Low | Low |
| **Tech Annoyance** | Medium (emails) | Low | Medium | Medium |
| **Implementation** | 1 week | 4 days | 1.5 weeks | 2-3 weeks |
| **Maintenance** | Low | Low | Low | Medium |
| **Scalability** | Good | Good | Good | Fair |
| **Recommended** | Maybe | Maybe | **YES** ✅ | No |

---

## Recommendation

### **Start with Option C (Email + Timestamp)**

**Why:**
1. **Best of Both Worlds** - Instant alert (email) + passive reminder (dashboard)
2. **Won't Miss Updates** - Multiple notification channels
3. **Reasonable Effort** - 1-1.5 weeks to implement
4. **Tech Controls Flow** - Can reply via email or use web interface
5. **Scalable** - Works well as case volume grows

**Implementation Order:**
1. Week 1: Add email notification when member updates
2. Week 1: Add timestamp display to dashboards  
3. Week 2: Test with real cases, gather feedback
4. Later: Consider Option D if needed

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
```
Task 1: Create email template
  - Location: cases/emails.py
  - Template: new_member_update_email.html
  - Variables: case_id, member_name, what_was_added, timestamp

Task 2: Add signal handler
  - Location: cases/signals.py
  - Listen for: member_document_uploaded event
  - Action: Trigger email to assigned tech

Task 3: Add timestamp display
  - Update: technician_dashboard.html
  - Update: manager_dashboard.html
  - Add column or update existing case row
```

### Phase 2: Testing (Week 1-2)
```
Task 1: Manual testing
  - Create test case
  - Member uploads doc
  - Verify email sent
  - Verify timestamp shows

Task 2: Edge case testing
  - Multiple uploads in quick succession
  - Tech manually edits due date (should trigger separately)
  - Cases with no assigned tech yet

Task 3: Feedback gathering
  - Ask techs: Email formatting OK?
  - Dashboard timestamp clear?
  - Want to adjust frequency?
```

### Phase 3: Refinement (Ongoing)
```
After launch:
- Monitor email delivery rates
- Gather tech feedback
- Adjust email frequency if needed
- Consider Option D modal if email not enough
```

---

## FAQ

### Q: Will tech get an email every time member uploads a document?
**A:** Yes, one email per upload. If you want to batch emails, we can do that in Phase 3.

### Q: Can tech opt out of emails?
**A:** Not in Phase 1. We can add notification preferences in Phase 3 if desired.

### Q: What if tech is on vacation?
**A:** Email still goes to them. Consider adding "delegate to manager" in future version.

### Q: Will old cases show a timestamp?
**A:** No, only cases with actual member updates post-submission. Old cases get timestamp of first member update.

### Q: Can we see what was added in the email?
**A:** Yes, email will show document name, size, date. Full details available by clicking "View Case" link.

### Q: What if no tech is assigned yet?
**A:** Email goes to case manager or admin instead. Need to define fallback logic in Phase 1.

### Q: How long does timestamp stay visible?
**A:** Indefinitely, unless you set a rule to hide after X days. Recommend: Always visible (helpful context).

### Q: Can member see the badge/timestamp?
**A:** No, it's tech-only. Member can see their own activity in case detail page.

### Q: What about documents uploaded by advisors (on behalf)?
**A:** Same treatment as member uploads = email + timestamp (assuming you want advisor uploads tracked too).

### Q: Will this affect performance?
**A:** Minimal impact. Adding one timestamp field and email queue is low overhead. Test with 100+ cases to be sure.

---

## Related Documents

- [POST_SUBMISSION_MODIFICATIONS_ANALYSIS.md](POST_SUBMISSION_MODIFICATIONS_ANALYSIS.md) - Full technical analysis of all post-submission options
- [AUDIT_TRAIL_IMPLEMENTATION_COMPLETE.md](AUDIT_TRAIL_IMPLEMENTATION_COMPLETE.md) - How audit logging works
- [DUE_DATE_URGENCY_BEHAVIOR_ANALYSIS.md](DUE_DATE_URGENCY_BEHAVIOR_ANALYSIS.md) - Due date change behavior

---

## Quick Decision Checklist

When deciding, ask yourself:

- [ ] Do techs currently miss member updates? → **Yes = Need notifications**
- [ ] How important is instant notification? → **Very = Need email**
- [ ] Can tech check dashboard regularly? → **No = Need email**
- [ ] How many cases per tech on average? → **20+ = Definitely need email**
- [ ] Do you want redundancy (email + dashboard)? → **Yes = Choose Option C**

---

**Last Reviewed:** January 23, 2026  
**Next Review:** After Phase 1 implementation  
**Owner:** Product Team  
**Status:** Ready for Decision
