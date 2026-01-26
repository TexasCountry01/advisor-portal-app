```plaintext
SCENARIO 5: Scheduled Release

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 5: Scheduled Release                                   │
└─────────────────────────────────────────────────────────────────┘

START: Tech completes investigation
Status: accepted
        │
        ▼
Tech: Uploads Report
        │
        ▼
Tech: Marks Case Complete
Modal: Release timing options
        │
        ├─ Option A: Release Now
        │
        └─ Option B: Schedule Release
            Picks: "Tomorrow at 9:00 AM"
        │
        ▼
Status: accepted → completed
Scheduled: Tomorrow 9:00 AM
        │
        ▼
Member: CANNOT SEE CASE YET
        │
        ▼
TIME PASSES: Tomorrow 9:00 AM
        │
        ▼
System: Auto-releases case at scheduled time
        │
        ▼
Member: Receives Email
"Your case report is ready"
        │
        ▼
Member: Downloads Report
        │
        ▼
END: Case Archived

```
