```plaintext
SCENARIO 3: Case Put on Hold

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 3: Case Put on Hold                                    │
└─────────────────────────────────────────────────────────────────┘

START: Tech is investigating case
Status: accepted
        │
        ▼
Tech: Encounters Issue
Need info from outside source
        │
        ▼
Tech: Clicks "Put on Hold"
Selects: Hold reason
Duration: Until problem is solved
Timestamp: Central Time Zone
        │
        ▼
Status: accepted → hold
Hold duration tracked: Central Time Zone
(Admin Dashboard shows cases on hold)
        │
        ▼
Member: Receives Hold Notification Email
"Your case is on hold - reason given"
(Email timestamp: Central Time)
        │
        ▼
Member: Can Upload Documents During Hold
Member: Can Add Comments
(Timestamps tracked in Central Time)
        │
        ▼
Member: Uploads Documents
        │
        ▼
Tech: Sees Member Has Updated
        │
        ▼
Tech: Reviews Member Upload
Assessment: "This solves the problem"
        │
        ▼
Tech: Clicks "Resume Processing"
Adds: Reason for resuming
Status: hold → accepted
        │
        ▼
Member: Receives Resume Notification
"Your case processing has resumed"
        │
        ▼
Tech: Continues Investigation
        │
        ▼
Tech: Completes Case
        │
        ▼
Member: Receives Report
        │
        ▼
END: Case Archived

```
