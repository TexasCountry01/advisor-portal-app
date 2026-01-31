```plaintext
SCENARIO 6: Member Requests Modification

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 6: Member Requests Modification                        │
└─────────────────────────────────────────────────────────────────┘

START: Member has completed case
Status: completed
Days since release: Less than 60 days
(Timestamp from Central Time Zone)
        │
        ▼
Member: Reviews Report
Notices: Possible error
        │
        ▼
Member: Within 60-day window?
        │
        ├─ YES:
        │
        ▼
Member: Clicks "Request Modification"
Modal: Reason for modification
Input: "Q3-Q4 calculations appear incorrect"
Optional: Upload docs
Timestamp: Central Time Zone
        │
        ▼
NEW CASE CREATED:
Status: submitted
Linked to: Original case
Created timestamp: Central Time Zone
(Admin can track modifications from Admin Dashboard)
        │
        ▼
Original Tech: Receives Notification
"Modification requested for case [ID]"
"New case: [ID]"
(Notification timestamp: Central Time)
        │
        ▼
Tech: Accepts Modification Case
        │
        ▼
Tech: Completes Modification
        │
        ▼
Member: Receives Corrected Report
        │
        ├─ Can see: Original case (unchanged)
        └─ Can see: Modification case (corrected)
        │
        ▼
END: Both cases archived
    Both timestamps logged: Central Time Zone
        │
        │
        │
        ├─ NO (60+ days):
        │
        └─ Modification button: DISABLED
           Member can: Ask a Question instead
           (No time limit - always available)

```
