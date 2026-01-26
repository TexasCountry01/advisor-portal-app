```plaintext
SCENARIO 1: Happy Path - Standard Processing

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 1: Happy Path - Standard Processing                    │
└─────────────────────────────────────────────────────────────────┘

START: Member logs in
        │
        ▼
Create Draft Case (FFF form + docs)
Status: draft
        │
        ▼
Submit Case (validation check)
Status: draft → submitted
        │
        ▼
Appears in Unassigned Queue
        │
        ▼
Tech: Review & Accept
Decision: Tier=1, Credit=1.5
Status: submitted → accepted
        │
        ▼
Tech: Investigates (4-12 hours)
        ├─ Reviews FFF data
        ├─ Checks documents
        ├─ External research
        └─ Status: accepted (no change)
        │
        ▼
Tech: Optional - Add Internal Notes
(Memo for self, not visible to member)
        │
        ▼
Tech: Optional - Ask Member Question
Public comment: "Can you clarify X?"
        │
        ▼
Member: Responds to Question
Comment + possible doc upload
        │
        ▼
Tech: Reviews Member Response
Reads comment & docs
        │
        ▼
Tech: Completes Investigation
        │
        ▼
Tech: Uploads Report
Document type: 'report'
        │
        ▼
Tech: Marks Case Complete
Selects: "Release Now"
Status: accepted → completed
        │
        ▼
Member: Receives Report
        │
        ▼
END: Case Archived

```
