```plaintext
SCENARIO 10: Manager Monitoring & Reporting

┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 10: Manager Monitoring & Reporting                     │
└─────────────────────────────────────────────────────────────────┘

START: Manager logs in
Role: Manager (read-only analytics access)
        │
        ▼
Manager: Views Dashboard
Sees: Key metrics and KPIs
        ├─ Total cases completed
        ├─ Average processing time
        ├─ Cases in-progress
        └─ Team productivity stats
        │
        ▼
Manager: Reviews Team Performance
Can see: Individual technician metrics
        ├─ Cases handled by Tech A
        ├─ Cases handled by Tech B
        ├─ Average completion time per person
        └─ Cases on hold (pending resolution)
        │
        ▼
Manager: Views Completed Cases List
Can filter/sort by:
        ├─ Date range
        ├─ Technician
        ├─ Case status
        └─ Tier/credit value
        │
        ▼
Manager: Opens Case Detail (VIEW ONLY)
Sees: Full case history, notes, documents, report
Can read but NOT edit or modify
        │
        ▼
Manager: Generates Reports
Options:
        ├─ Monthly productivity report
        ├─ Team performance summary
        ├─ Case metrics breakdown
        └─ Export data for analysis
        │
        ▼
Manager: Monitors Work in Progress
Can see: Currently assigned cases by technician
        ├─ Which tech has case
        ├─ Current status (submitted/accepted/hold)
        ├─ How long case has been assigned
        └─ Any cases on hold (reason + duration)
        │
        ▼
Manager: No Edit Access
        ├─ Cannot modify cases
        ├─ Cannot reopen completed cases
        ├─ Cannot change assignments (tech can self-reassign)
        └─ Cannot approve or reject work
        │
        ▼
Manager: END - Reports Generated
Data ready for analysis and strategic planning

```
