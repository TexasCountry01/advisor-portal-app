```plaintext
SCENARIO 2: Information Request & Resubmission

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 2: Information Request & Resubmission                  │
└─────────────────────────────────────────────────────────────────┘

START: Member submits incomplete case
Status: submitted
Timestamp: Central Time Zone
(Admin Dashboard shows in submitted queue)
        │
        ▼
Tech: Reviews Case
Finds: Missing information
        │
        ▼
Tech: Clicks "Request More Info"
Modal: Select rejection reason
Add notes: "Need X documents"
        │
        ▼
Status: submitted → needs_resubmission
Timestamp logged: Central Time Zone
        │
        ▼
Member: Receives Rejection Email
"Additional information needed for case"
(Email timestamp: Central Time)
        │
        ▼
Member: Uploads Missing Documents
        │
        ▼
Member: Clicks "Resubmit Case"
Status: needs_resubmission → submitted
        │
        ▼
Case: Back in Tech's Queue
Tech sees: "Resubmitted case - review required"
(Admin monitors from Admin Dashboard)
        │
        ▼
Tech: Re-Reviews Case
Checks: Missing info now complete
        │
        ▼
Tech: Reviews & Accepts
Status: submitted → accepted
        │
        ▼
Tech: Investigates
        │
        ▼
Tech: Completes & Releases
Status: accepted → completed
        │
        ▼
Member: Gets Report
        │
        ▼
END: Case Archived

```
