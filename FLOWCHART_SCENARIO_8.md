```plaintext
SCENARIO 8: Modification Outside 60-Day Window

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 8: 60-Day Window Enforcement                           │
└─────────────────────────────────────────────────────────────────┘

START: Member reviews old case
Status: completed
Days since release: 65 days (PAST 60-day window)
Window calculated: Central Time Zone basis
(Admin can verify from audit trail)
        │
        ▼
Member: Notices Issue
Wants: Request modification
        │
        ▼
"Request Modification" Button?
        │
        ├─ DISABLED
        ├─ Cannot click
        └─ Message: "Requests only available within 60 days"
            (60-day window based on Central Time release)
        │
        ▼
Member: Alternative Action
        │
        ▼
Member: Clicks "Ask a Question"
(No time limit - always available)
        │
        ▼
Member: Types Question
"I think the calculation might be wrong"
Question timestamp: Central Time Zone
        │
        ▼
Tech: Receives Question
Question notification with timestamp
        │
        ▼
Tech: Responds
        │
        ├─ "The calculation was correct because..."
        │
        └─ OR: "You're right, let me review"
        │
        ▼
Member: Gets Response
Response timestamp: Central Time Zone
(Visible in case audit trail)
        │
        ▼
END: Case stays archived
    No new modification case
    Q&A logged in audit trail with Central Time timestamps

```