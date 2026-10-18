"""The default years of the derived data and reports, in one place.

The defaults stay at the years of the committed outputs, so that make
reproduces them; see docs/reference/make-targets.md.
"""

from datetime import date

# The last year of the 3-, 5- and 10-year summaries
SUMMARY_END_YEAR = 2024
# The year of the community recognition report
RECOGNITION_YEAR = 2025


def window(length, end=SUMMARY_END_YEAR):
    """The `length` years up to and including `end`."""
    return list(range(end - length + 1, end + 1))


def last_completed_year(today=None):
    """The last calendar year that has ended."""
    return (today or date.today()).year - 1
