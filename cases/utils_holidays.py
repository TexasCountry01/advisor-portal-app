"""
Holiday-aware due date utilities.

Federal holidays are sourced from the python-holidays library and synced
into the Holiday database table (current year + next year) each time the
admin opens the Case Defaults section of System Settings.

calculate_due_date() is the single entry point used everywhere a default
due date needs to be computed.
"""

from datetime import date, timedelta

import holidays as holidays_lib


def sync_federal_holidays(years=None):
    """
    Sync US federal holidays for the given years into the Holiday table.
    Only creates missing entries — never overwrites admin's active/inactive choice.

    Args:
        years: iterable of int years, e.g. [2026, 2027].
               Defaults to current year + next year.
    """
    from core.models import Holiday

    if years is None:
        today = date.today()
        years = [today.year, today.year + 1]

    us_holidays = holidays_lib.US(years=years)

    for holiday_date, holiday_name in us_holidays.items():
        Holiday.objects.get_or_create(
            date=holiday_date,
            defaults={
                'name': holiday_name,
                'is_custom': False,
                'active': True,
            },
        )


def get_holidays_in_window(start_date, end_date):
    """
    Return a QuerySet of active Holiday objects strictly between
    start_date (exclusive) and end_date (inclusive).
    """
    from core.models import Holiday

    return Holiday.objects.filter(
        active=True,
        date__gt=start_date,
        date__lte=end_date,
    ).order_by('date')


def calculate_due_date(from_date, base_days=7):
    """
    Calculate the holiday-adjusted due date.

    Starts with from_date + base_days, then extends by 1 day for each
    active holiday that falls within the window.  Re-checks after each
    extension so that a second holiday newly included in the extended
    window is also accounted for.

    Args:
        from_date: date — the submission date (today for new cases)
        base_days: int — the normal turnaround (from SystemSettings)

    Returns:
        (due_date, holidays_in_window)
        due_date           — adjusted date object
        holidays_in_window — list of Holiday objects that caused the extension
    """
    due = from_date + timedelta(days=base_days)
    seen_holiday_ids = set()

    # Cap iterations to prevent an infinite loop if holiday data is unusual
    for _ in range(20):
        new_holidays = get_holidays_in_window(from_date, due).exclude(
            pk__in=seen_holiday_ids
        )
        if not new_holidays.exists():
            break
        for h in new_holidays:
            seen_holiday_ids.add(h.pk)
            due += timedelta(days=1)

    holidays_in_window = list(
        get_holidays_in_window(from_date, due).filter(pk__in=seen_holiday_ids)
        if seen_holiday_ids
        else []
    )
    return due, holidays_in_window
