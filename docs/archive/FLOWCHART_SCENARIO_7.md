```plaintext
SCENARIO 7: Complex Hold & Resume Cycle

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 7: Multiple Hold/Resume Cycles                         │
└─────────────────────────────────────────────────────────────────┘

START: Tech investigating
Status: accepted
        │
        ▼
HOLD CYCLE #1
        │
        ▼
Tech: Put on Hold #1
Reason: "Waiting for employment verification"
Hold start timestamp: Central Time Zone
(Admin Dashboard shows hold duration)
        │
        ▼
Member: Notified - Case on Hold
Notification sent with timestamp
        │
        ▼
Member: Uploads Employment Letter
Upload timestamp: Central Time Zone
        │
        ▼
Tech: Reviews Upload
Assessment: "Good, acceptable"
        │
        ▼
Tech: Resume from Hold #1
Status: hold → accepted
Hold duration: Central Time Zone tracked
(Admin notified of hold completion)
        │
        ▼
Member: Notified - Case Resumed
Notification with resume timestamp: Central Time
        │
        ▼
Tech: Continues Investigation
        │
        ▼
HOLD CYCLE #2
        │
        ▼
Tech: Put on Hold #2
Reason: "Awaiting manager approval"
Hold start timestamp: Central Time Zone
        │
        ▼
Member: Notified - Case on Hold (Again)
        │
        ▼
Manager: Approves
        │
        ▼
Tech: Resume from Hold #2
Status: hold → accepted
Hold duration logged: Central Time Zone
        │
        ▼
Member: Notified - Case Resumed
        │
        ▼
Tech: Completes Case
        │
        ▼
Member: Receives Report
        │
        ▼
END: Case Archived
    Admin Dashboard shows complete hold history
    All timestamps: Central Time Zone

```