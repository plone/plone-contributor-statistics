"""The default years live in one place (repository layout)."""

from datetime import date

from scripts.lib import years


def test_default_years_follow_the_last_completed_year():
    # A new year needs no code change: the defaults move on when a year ends
    last = years.last_completed_year()
    assert years.SUMMARY_END_YEAR == last
    assert years.RECOGNITION_YEAR == last
    assert years.window(3) == [last - 2, last - 1, last]
    assert years.window(10) == list(range(last - 9, last + 1))


def test_window_ends_with_the_given_year():
    assert years.window(3, end=2025) == [2023, 2024, 2025]


def test_last_completed_year():
    assert years.last_completed_year(date(2026, 10, 18)) == 2025
    assert years.last_completed_year(date(2026, 1, 1)) == 2025
