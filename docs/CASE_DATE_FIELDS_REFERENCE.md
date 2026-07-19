# Case Date Fields — Reference Guide

**Purpose:** Clarify the terminology and timing of every date recorded on a case, from member submission through advisor notification.

---

## The Complete Case Timeline

STANDARD PATH — No L3 review, immediate release
================================================

    Member submits case
        |
        +--> DATE RECORDED: "date_submitted"
             Auto-recorded the moment the member clicks Submit
        |
        v
    Case sits in queue  (Status: submitted)
        |
    Tech accepts / takes the case
        |
        +--> DATE RECORDED: "date_accepted"
             Auto-recorded the moment the tech accepts
        |
        v
    Tech works the case  (Status: accepted)
        |
    Tech clicks "Release Case" on Pre-Completion Review
        |
        +--> DATE RECORDED: "date_completed"
             Auto-recorded — this is when the TECH IS DONE.
             This is NOT when the advisor sees the report.
        |
        v
    Report immediately visible to advisor  (Status: completed)
        |
        +--> DATE RECORDED: "actual_release_date"
             Auto-recorded — same moment as date_completed for immediate release
        |
        v
    Email notification sent to advisor
        |
        +--> DATE RECORDED: "actual_email_sent_date"
             Auto-recorded by email service after confirming successful delivery
        |
        v
    Advisor notified  [END]


WITH L3 REVIEW — L1 tech submits case for senior tech approval
==============================================================

    Tech works the case  (Status: accepted)
        |
    L1 Tech clicks "Submit for Review"
        |
        +--> DATE RECORDED: "CaseReviewHistory.reviewed_at"
             Auto-recorded — this is the "submitted for review" date.
             Stored on a separate review record, not the main case.
             review_action = "submitted_for_review"
        |
        v
    Awaiting L3 review  (Status: pending_review)
        |
        +-- L3 requests revisions --> Tech revises --> Submit for Review again
        |                                              (new review record created,
        |                                               new reviewed_at recorded)
        |
        +-- L3 approves --> Tech clicks "Release Case"
                                |
                                +--> DATE RECORDED: "date_completed"
                                     (Tech done — continue to release path above)


WITH SCHEDULED RELEASE — Tech holds the report for a future date
================================================================

    Tech clicks "Release Case" and picks a future date/time
        |
        +--> DATE RECORDED: "date_completed"
             Tech is done NOW, at this moment
        |
        +--> DATE RECORDED: "scheduled_release_date"
             Future date/time chosen by the tech
        |
        +--> DATE RECORDED: "scheduled_email_date"
             Same future date/time — email is queued to send then
        |
        v
    Report held, NOT yet visible to advisor  (Status: completed but unreleased)
        |
    [Cron job runs automatically when scheduled time arrives]
        |
        +--> DATE RECORDED: "actual_release_date"
             Auto-recorded by the cron job
        |
        v
    Report now visible to advisor
        |
    Email service sends notification
        |
        +--> DATE RECORDED: "actual_email_sent_date"
             Auto-recorded after confirmed delivery
        |
        v
    Advisor notified  [END]

---

## Date Field Quick Reference

1. date_submitted
   Label: Submitted
   Set by: System (automatic)
   When: The instant the member clicks Submit

2. date_accepted
   Label: Accepted
   Set by: System (automatic)
   When: The instant a tech accepts / takes the case

3. date_due
   Label: Due Date
   Set by: Tech or Admin (manual)
   When: Assigned manually when the tech sets the deadline

4. date_scheduled
   Label: Scheduled Date
   Set by: Tech or Admin (manual)
   When: Optional planning date set by the tech

5. CaseReviewHistory.reviewed_at
   Label: Submitted for Review
   Set by: System (automatic)
   When: The instant the L1 tech clicks Submit for Review.
         Stored on a separate review audit record, not the main case.

6. date_completed
   Label: Tech Finished
   Set by: System (automatic)
   When: The instant the tech clicks Release Case on the Pre-Completion Review page.
         This is when the tech's work is done — NOT when the advisor sees the report.

7. scheduled_release_date
   Label: Release Scheduled For
   Set by: System (based on tech's choice)
   When: Set at the same moment as date_completed, only if the tech
         chose a future release time. Null for immediate releases.

8. actual_release_date
   Label: Released to Advisor
   Set by: System (automatic)
   When: Immediate release — same moment as date_completed.
         Scheduled release — set by the cron job when the scheduled time arrives.

9. scheduled_email_date
   Label: Email Scheduled For
   Set by: System (set together with scheduled_release_date)
   When: Same moment as scheduled_release_date.
         The system uses this to know when to send the notification email.

10. actual_email_sent_date
    Label: Email Sent to Advisor
    Set by: Email service (automatic)
    When: The instant the notification email is successfully delivered.

---

## The Critical Distinction: Completed vs. Released

This is the most common source of confusion.

    date_completed       =  When the TECH finished the work
    actual_release_date  =  When the ADVISOR can see the report
    actual_email_sent_date  =  When the ADVISOR received the email

These three can all be different:

Scenario 1 — Tech releases immediately
    date_completed:          Monday 9:00 AM
    actual_release_date:     Monday 9:00 AM
    actual_email_sent_date:  Monday 9:00 AM

Scenario 2 — Tech schedules release for next morning
    date_completed:          Monday 9:00 AM
    actual_release_date:     Tuesday 8:00 AM  (set by cron job)
    actual_email_sent_date:  Tuesday 8:00 AM  (set by email service)

Scenario 3 — Tech schedules release for a specific future date
    date_completed:          Monday 9:00 AM
    actual_release_date:     Thursday 10:00 AM  (set by cron job)
    actual_email_sent_date:  Thursday 10:00 AM  (set by email service)

The cron job is the automated system process that runs on a schedule and
checks whether any scheduled releases are due. When it finds one it:
    1. Sets actual_release_date (marks the case as released to the advisor)
    2. Triggers the email service
    3. Email service sets actual_email_sent_date after confirming delivery

---

## The L3 Review Path — Multiple Records per Case

When an L1 tech submits for review, a separate CaseReviewHistory record is created.
One case can have multiple review records if revisions are requested:

    Record 1:  reviewed_at = Mon 2:00 PM    action = submitted_for_review
    Record 2:  reviewed_at = Mon 4:30 PM    action = revisions_requested
    Record 3:  reviewed_at = Tue 9:00 AM    action = resubmitted
    Record 4:  reviewed_at = Tue 11:00 AM   action = approved

When the Performance Dashboard or Scorecard shows "Submitted for Review," it counts
review records with action = submitted_for_review — not unique cases. A case that
is submitted, revised, and resubmitted counts as TWO submission events.

---

## Which Date Each Performance Metric Uses

REPORTS GENERATED
    Date used:   date_completed
    Measures:    When the tech finished — counts cases where the tech's
                 completion date falls within the selected period

SUBMITTED FOR REVIEW
    Date used:   CaseReviewHistory.reviewed_at
    Measures:    When the L1 clicked Submit for Review
                 (counts events, not unique cases)

ON-TIME DELIVERY %
    Date used:   date_completed compared to date_due
    Measures:    Was the tech done on or before the due date?

PROFEDS ERRORS
    Date used:   date_submitted of the modification case
    Measures:    When the member reported the error

PRODUCTION CYCLE TIME
    Date used:   date_submitted through date_completed
    Measures:    Total days from member submission to tech finishing

READINESS WINDOW
    Date used:   date_completed compared to date_due
    Measures:    How many days early (or late) the tech finished

REPORT ACCURACY %
    Date used:   date_completed
    Measures:    Completed cases with no ProFeds error flag,
                 as a percentage of all completed cases

INITIAL SUBMISSIONS
    Date used:   date_submitted
    Measures:    When the advisor originally submitted the case

NOTE: No performance metric currently uses actual_release_date or
actual_email_sent_date. Those fields track the advisor's experience
(when they received the report), not the technician's work.

