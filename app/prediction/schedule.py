"""The refit schedule shared by the trained models: once a week, on Monday."""

from datetime import date, timedelta


def week_start(day: date) -> date:
    """Return the Monday of the calendar week that contains ``day``."""
    return day - timedelta(days=day.weekday())
