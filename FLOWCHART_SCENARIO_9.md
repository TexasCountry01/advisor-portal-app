```plaintext
SCENARIO 9: Multiple Document Requests (Iterative)

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 9: Back-and-Forth Questions (No Holds)                 │
└─────────────────────────────────────────────────────────────────┘

START: Case accepted
Status: accepted (stays accepted throughout)
(Admin Dashboard shows in active cases)
        │
        ▼
REQUEST #1
        │
        ▼
Tech: Asks Public Question
"Can you upload medical report?"
Question timestamp: Central Time Zone
        │
        ▼
Member: Sees Question Badge
        │
        ▼
Member: Uploads Document
"Medical Report"
Upload timestamp: Central Time Zone
        │
        ▼
Member: Adds Response
"Here's my medical report"
Response timestamp: Central Time Zone
        │
        ▼
REQUEST #2
        │
        ▼
Tech: Reviews Upload
Needs: Clarification
        │
        ▼
Tech: Asks 2nd Question
"Can you clarify treatment dates?"
Question timestamp: Central Time Zone
        │
        ▼
Member: Uploads Supplement
"Treatment Timeline"
        │
        ▼
Member: Responds
"I've attached the timeline"
Response timestamp: Central Time Zone
        │
        ▼
REQUEST #3
        │
        ▼
Tech: Asks Final Question
"Any employment after 2023?"
Question timestamp: Central Time Zone
        │
        ▼
Member: Final Answer
"No, on benefits"
Response timestamp: Central Time Zone
        │
        ▼
Tech: All Info Gathered
        │
        ▼
Tech: Complete Case
        │
        ▼
Member: Receives Report
        │
        ▼
END: Case Archived
    3 rounds of Q&A (all timestamped: Central Time)
    No holds needed
    Admin Dashboard shows completion
    Audit trail complete with all Central Time timestamps

```
