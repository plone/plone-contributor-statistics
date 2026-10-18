"""The default years of the derived data and reports, in one place.

The defaults follow the last completed year, so a new year needs no code
change; see docs/reference/make-targets.md.
"""

from datetime import date


def last_completed_year(today=None):
    """The last calendar year that has ended."""
    return (today or date.today()).year - 1


# The last year of the 3-, 5- and 10-year summaries
SUMMARY_END_YEAR = last_completed_year()
# The year of the community recognition report
RECOGNITION_YEAR = last_completed_year()


def window(length, end=SUMMARY_END_YEAR):
    """The `length` years up to and including `end`."""
    return list(range(end - length + 1, end + 1))
