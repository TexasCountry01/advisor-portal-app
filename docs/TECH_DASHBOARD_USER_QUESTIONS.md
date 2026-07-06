# Technician Performance Dashboard — Clarifying Questions

Before building, we need answers to the following questions.

---

## Questions

**1. Reports Generated**
Should this count:
- (a) Only fully released/completed cases, or
- (b) Cases submitted for internal quality review (before final release), or
- (c) Both combined into one number?

**2. On-Time Delivery % — Denominator**
"# of reports due" — does that mean:
- (a) Cases whose **due date falls** within the selected date range, or
- (b) Cases **completed** within the selected date range?

**3. Report Accuracy — What counts as an "error"?**
Errors are exclusively created by members — the system records one when a member submits a modification request and checks "Is this a ProFeds error?" This is the only source of error data. Confirming: is that the correct and complete definition of an "error" for this metric?

**4. Report Accuracy — Lag awareness**
Because only a member can flag an error, and they may not do so until days or weeks after receiving the report, a case completed in the last 7 days may not show an error yet. Is that acceptable for this metric?

**5. Errors — How to count**
If one case has three error-related modification requests, does that count as:
- (a) 1 error (one case flagged), or
- (b) 3 errors (three events)?

**6. Dashboard audience**
Is this view for administrators/managers only, or will individual technicians also see their own numbers?

---

## Already Built

Two of the five requested metrics are already available as standalone reports:

| Requested Metric | Existing Report | Location |
|---|---|---|
| Report On-Time Delivery % | Due Date Compliance Report | Reports & Analytics → Due Date Compliance |
| Errors (ProFeds) | ProFeds Error Tracking Report | Reports & Analytics → ProFeds Error Tracking |

Both support custom date range filtering today. If the goal is a single consolidated view, these can be pulled into a dashboard alongside the three remaining metrics.
