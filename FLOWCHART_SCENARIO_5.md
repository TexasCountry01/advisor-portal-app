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
            Picks: "Tomorrow at 9:00 AM" (Central Time)
        │
        ▼
Status: accepted → completed
Scheduled: Tomorrow 9:00 AM (Central Time Zone)
(Admin notified of scheduled release)
        │
        ▼
Member: CANNOT SEE CASE YET
        │
        ▼
TIME PASSES: Tomorrow 9:00 AM (Central Time)
        │
        ▼
System: Auto-releases case at scheduled time
Release executed with Central Time Zone timestamp
(Audit trail logged)
        │
        ▼
Member: Receives Email
"Your case report is ready"
(Email sent at scheduled time, Central Time)
        │
        ▼
Member: Downloads Report
        │
        ▼
END: Case Archived
    Admin Dashboard updated

```