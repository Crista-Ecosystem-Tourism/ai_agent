"""Calendar-day streak rules shared by every game read and write path."""

from datetime import date, timedelta


def next_streak(streak: int, last_activity_on: date | None, activity_on: date) -> int:
    """Streak after activity on ``activity_on``; repeated activity on one day counts once."""
    if last_activity_on == activity_on:
        return streak
    if last_activity_on == activity_on - timedelta(days=1):
        return streak + 1
    return 1


def visible_streak(streak: int, last_activity_on: date | None, today: date) -> int:
    """Streak as of ``today``: still alive until today's activity window closes, else broken."""
    if last_activity_on is None:
        return 0
    if last_activity_on in (today, today - timedelta(days=1)):
        return streak
    return 0
