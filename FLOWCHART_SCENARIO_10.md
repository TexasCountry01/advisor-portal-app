```plaintext
SCENARIO 10: Manager Quality Review

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 10: Manager Quality Review                             │
└─────────────────────────────────────────────────────────────────┘

START: Case is completed
Status: completed
        │
        ▼
Manager: Reviews Completed Cases
Can see: All completed cases
        │
        ▼
Manager: Opens Case Detail
Sees: Full case, notes, documents, report
        │
        ▼
PATH A: APPROVAL
        │
        ├─ Manager Reviews Work
        │  Assessment: "Excellent, calculations correct"
        │  │
        │  ▼
        │  Manager: Optional - Add Review Note
        │  Content: "Approved"
        │  │
        │  ▼
        │  Tech: Sees Manager Feedback
        │  │
        │  ▼
        │  END: Case stays completed ✅
        │
        │
        │
        PATH B: ISSUES FOUND
        │
        ├─ Manager Reviews Work
        │  Issue: "Q3 calculation appears incorrect"
        │  │
        │  ▼
        │  Manager: Clicks "Reopen for Correction"
        │  Reason: "Q3 calculation error"
        │  │
        │  ▼
        │  Case Status: completed → reopen_for_correction
        │  │
        │  ▼
        │  Tech: Receives Notification
        │  "Case reopened for correction"
        │  "Reason: Q3 calculation error"
        │  │
        │  ▼
        │  Tech: Investigates Issue
        │  Recalculates Q3
        │  Finds: Manager is correct
        │  │
        │  ▼
        │  Tech: Fixes and Uploads Corrected Report
        │  │
        │  ▼
        │  Case Status: reopen_for_correction → completed
        │  │
        │  ▼
        │  Manager: Re-Reviews
        │  │
        │  ▼
        │  END: Case Corrected & Approved ✅
        │
        │
        ▼
   Case Finalized

```
