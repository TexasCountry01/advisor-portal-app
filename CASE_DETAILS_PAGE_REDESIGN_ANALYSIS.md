# Case Details Page Redesign Analysis

**Date:** January 24, 2026  
**Context:** Feedback from case details page UX review - both member and benefits-technician views

---

## Overview

The case details page is too long, confusing, and contains functionality that doesn't work as intended. Three main improvements needed:

1. Fix "Resubmit Case" button logic and UX
2. Implement case modification tracking (sub-cases or associated cases)
3. Redesign notes sections for dialogue-style communication

---

## Issue #1: Resubmit Button Logic & Page Length

### Current Problem

**Button Behavior:**
- "Resubmit Case" button appears for cases that are NOT completed
- When user uploads a document and clicks "Resubmit", error displays: "Only completed cases can be resubmitted"
- Confusing UX - button shouldn't be clickable/visible for incomplete cases

**Page Length Issue:**
- Upload Documents section clutters the page
- Resubmit button adds to confusion
- Entire section could be replaced with cleaner UI

### Proposed Solution

**Option A: Hidden Until Completion (Recommended)**

1. **Hide "Resubmit Case" button** until case status = 'completed'
2. **Replace entire upload/resubmit section** with a single button: **"Request a Modification"**
3. **"Request a Modification" button:**
   - Only visible after case is marked as "Complete"
   - Launches a pop-up modal (keeps page clean)
   - Modal contains:
     - Reason for modification
     - Document upload field
     - "Submit Modification Request" button
   - Reduces page clutter significantly

### Implementation Details

**Current State:**
```
Case Status: Draft → Submitted → Accepted → Completed
             ↑
             Upload section visible throughout
             Resubmit button visible but broken
```

**Proposed State:**
```
Case Status: Draft → Submitted → Accepted → Completed
                                              ↓
                                    "Request a Modification"
                                    button becomes visible
                                    (launches modal)
```

**Button Visibility:**
| Case Status | Upload Section | Resubmit Button | Req. Mod. Button |
|-------------|----------------|-----------------|------------------|
| Draft | ✅ Show | ❌ Hide | ❌ Hide |
| Submitted | ✅ Show | ❌ Hide | ❌ Hide |
| Accepted | ✅ Show | ❌ Hide | ❌ Hide |
| Completed | ❌ Hide | ❌ Hide | ✅ Show |
| Resubmitted | ❌ Hide | ❌ Hide | ❌ Hide |

---

## Issue #2: Case Modification Tracking

### Current Problem

**When case is resubmitted for modification:**
- Original case submission date gets overwritten
- Original completion date gets overwritten
- New documents mixed with original documents
- Cannot independently track modification timeline
- No way to differentiate between original and modified submission

### Proposed Solution Options

**Option A: Sub-Cases (Recommended)**

Create a parent-child relationship:
- Original case remains unchanged (original dates preserved)
- Modification appears as a "sub-case" nested under the original
- Sub-case has own:
  - Due date (independent)
  - Completion date (independent)
  - Document list (separate from original)
  - Status timeline (separate tracking)

**Database Model:**
```
Case (Original)
├── ID: W5000-2026-01-0009
├── Status: Completed
├── Created: 01/11/2026
├── Completed: 01/15/2026
├── Documents: [original 3 files]
│
└── SubCase (Modification #1)
    ├── ID: W5000-2026-01-0009-MOD-001
    ├── Parent Case: W5000-2026-01-0009
    ├── Modification Type: "Request new scenario"
    ├── Status: Completed
    ├── Created: 01/18/2026
    ├── Completed: 01/19/2026
    ├── Due Date: 01/25/2026
    ├── Documents: [new documents only]
    └── Original Due Date: 01/24/2026 (inherited from parent)
```

**Dashboard Display:**
```
W5000-2026-01-0009 (Completed - 01/15)
  ├─ Scenario: "Original submission"
  │  Due: 01/24/2026
  │  Status: Complete
  │
  └─ MOD-001 (Completed - 01/19)
     Scenario: "New scenario requested"
     Due: 01/25/2026
     Status: Complete
```

**Option B: Associated Cases**

Modification appears as separate case linked to original:
- Creates new case ID: W5000-2026-01-0010
- Links to original via "Related Cases" field
- Shows relationship in UI
- Less hierarchical, but still tracks separately

```
Case: W5000-2026-01-0009 (Original)
  Related Cases: [W5000-2026-01-0010]

Case: W5000-2026-01-0010 (Modification)
  Related Cases: [W5000-2026-01-0009]
```

### Recommendation

**Use Option A (Sub-Cases)** because:
- ✅ Keeps modification logically nested under original
- ✅ Preserves all original dates/data
- ✅ Easy to see full history of a member's request
- ✅ Separate due date tracking for modifications
- ✅ Independent document list
- ✅ Clear parent-child relationship

### Implementation Checklist

- [ ] Create `SubCase` model with:
  - `parent_case` (FK to Case)
  - `modification_type` (enum: "new_scenario", "fix_mistake", "additional_docs")
  - `created_at`, `due_date`, `completed_at`
  - `hold_reason`, `status` (independent status)
  
- [ ] Update Case model to include:
  - `subcases` reverse relationship
  - `is_subcase` boolean flag
  
- [ ] Modify case detail page to:
  - Show original case with all sub-cases nested below
  - Display each sub-case with independent dates
  - Show separate document lists
  
- [ ] Update dashboard to display sub-cases
  
- [ ] Create separate queue for sub-case modifications

---

## Issue #3: Notes Section Redesign

### Current Problem

**Two separate notes sections:**
- "Member Notes to Request Edit" (initiated by member)
- "Tech Notes" (initiated by technician)
- Displayed as separate blocks (not conversational)
- Hard to follow dialogue/context
- No clear back-and-forth communication flow

### Proposed Solution

**Dialogue-Style Notes Display**

Convert to conversation format like text messaging, with visual differentiation:

#### Option A: Offset Alignment (Left/Right)
```
┌─ Case Details ────────────────────────────────────────┐
│                                                        │
│ Member (01/11 @ 2:30 PM):                              │
│ "Hi, I need my benefits verified ASAP. I'm having     │
│  issues with my paperwork. Please let me know if you   │
│  need anything else from me."                          │
│                                            ┌─────────┐│
│                                            │ Tech    ││
│                                            │ (01/12  ││
│                                            │ @ 9:15  ││
│                                            │ AM):    ││
│                                            │         ││
│                                            │ Thanks, ││
│                                            │ I       ││
│                                            │ received││
│                                            │ your    ││
│                                            │ docs.   ││
│                                            │ Can you ││
│                                            │ clarify ││
│                                            │ the     ││
│                                            │ date of ││
│                                            │ service?││
│                                            └─────────┘│
│                                                        │
│ Member (01/12 @ 10:45 AM):                             │
│ "Date of service is 01/01/2026"                       │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Natural conversation flow
- ✅ Easy to follow context
- ✅ Timestamps clear
- ✅ Visual separation (left/right)
- ✅ Similar to familiar text message UI

#### Option B: Bold/Regular Text Differentiation

```
Member Notes (01/11 @ 2:30 PM):
**Hi, I need my benefits verified ASAP. I'm having issues with my paperwork. 
Please let me know if you need anything else from me.**

Tech Response (01/12 @ 9:15 AM):
Thanks, I received your docs. Can you clarify the date of service?

Member Response (01/12 @ 10:45 AM):
**Date of service is 01/01/2026**

Tech Response (01/13 @ 11:20 AM):
Perfect, got it. Processing your request now. Will have results by EOD today.
```

**Benefits:**
- ✅ Simple implementation
- ✅ Works well in email-like format
- ✅ Clear role distinction (bold = member, regular = tech)
- ✅ Chronological ordering natural

### Recommendation

**Use Option A (Offset Alignment)** because:
- ✅ Most similar to modern messaging apps (familiar to users)
- ✅ Visual offset makes it very clear who said what
- ✅ Better readability on longer messages
- ✅ More professional appearance

### Implementation Details

**HTML Structure:**
```html
<div class="notes-conversation">
  
  <div class="note member-note">
    <div class="note-header">
      <strong>Member</strong>
      <span class="timestamp">01/11 @ 2:30 PM</span>
    </div>
    <div class="note-body">
      Hi, I need my benefits verified ASAP...
    </div>
  </div>
  
  <div class="note tech-note">
    <div class="note-header">
      <strong>Technician</strong>
      <span class="timestamp">01/12 @ 9:15 AM</span>
    </div>
    <div class="note-body">
      Thanks, I received your docs...
    </div>
  </div>
  
</div>
```

**CSS Styling:**
```css
.notes-conversation {
  padding: 20px;
}

.note {
  margin-bottom: 20px;
  max-width: 70%;
  padding: 15px;
  border-radius: 8px;
}

.member-note {
  margin-left: 0;
  margin-right: auto;
  background-color: #e3f2fd;
  border-left: 4px solid #2196F3;
}

.tech-note {
  margin-left: auto;
  margin-right: 0;
  background-color: #f3e5f5;
  border-right: 4px solid #9c27b0;
}

.note-header {
  font-size: 12px;
  margin-bottom: 8px;
  color: #666;
}

.timestamp {
  float: right;
  font-size: 11px;
}

.note-body {
  line-height: 1.5;
  color: #333;
}
```

### Implementation Checklist

- [ ] Update Note model to include:
  - `role` (member or technician)
  - `created_at` timestamp
  - Sort notes chronologically
  
- [ ] Modify case_detail.html template:
  - Remove separate "Member Notes" and "Tech Notes" sections
  - Create single unified notes conversation display
  - Apply left/right offset styling
  - Add timestamps to each note
  
- [ ] Test with various note lengths/scenarios

---

## Summary of Changes

| Issue | Current | Proposed | Priority |
|-------|---------|----------|----------|
| Resubmit button | Broken for incomplete cases | Hide until completion, use "Request Modification" modal | High |
| Document uploads | Clutters page, overrides original dates | Move to pop-up modal | High |
| Case modifications | Overwrites original dates | Sub-cases with independent tracking | High |
| Notes display | Two separate blocks, not conversational | Dialogue-style conversation (left/right offset) | Medium |

---

## Files to Modify

1. **`cases/models.py`**
   - Add `SubCase` model (if using sub-cases approach)
   - Add fields to Case model
   
2. **`cases/views.py`**
   - Update `case_detail()` view to handle sub-cases
   - Update `put_case_on_hold()` for sub-case logic
   - Create `request_modification()` view for modal
   
3. **`cases/templates/cases/case_detail.html`**
   - Restructure notes section to dialogue format
   - Hide resubmit button until case complete
   - Move upload/resubmit to modal (only shown after completion)
   - Display sub-cases if applicable
   
4. **`cases/static/css/case_detail.css`** (or main stylesheet)
   - Add offset/dialogue styling for notes
   - Update modal styling for modifications

---

## Open Questions

1. Should member be able to request multiple modifications, or just one?
2. What should happen to original due date when modification is requested?
3. Should modification sub-cases appear in main dashboard or separate "Modifications" view?
4. For modifications - should we keep same assigned technician or allow reassignment?
5. Should sub-case modifications show as separate line items in reports, or grouped under original?
