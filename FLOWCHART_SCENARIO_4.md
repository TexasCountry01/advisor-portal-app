```plaintext
SCENARIO 4: Case Reassignment

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 4: Case Reassignment                                   │
└─────────────────────────────────────────────────────────────────┘

START: Case is being worked by Tech A
Status: accepted
Assigned To: Tech A
(Visible in Admin Dashboard)
        │
        ▼
Tech A: Cannot Continue
Reason: Vacation, sick, busy
        │
        ▼
Tech A: Clicks "Reassign"
Selects: New technician (Tech B)
Optional: Adds reason
Timestamp: Central Time Zone
        │
        ▼
Case Updated:
Status: accepted (UNCHANGED)
Assigned To: Tech A → Tech B
Reassignment logged: Central Time Zone
(Admin Dashboard updated in real-time)
        │
        ▼
Tech B: Receives Notification
"Case assigned to you"
(Notification timestamp: Central Time)
        │
        ▼
Tech B: Opens Case
Sees: All previous notes, documents, history
Sees: Reassignment reason & timestamp
        │
        ▼
Tech B: Continues Investigation
Same work as normal
        │
        ▼
Tech B: Completes & Releases
        │
        ▼
Member: Receives Report from Tech B
        │
        ▼
END: Case Archived

```