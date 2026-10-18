"""The default years live in one place (repository layout)."""

from datetime import date

from scripts.lib import years


def test_default_windows_unchanged():
    # Until the outputs are regenerated on purpose, make reproduces the committed files
    assert years.window(3) == [2022, 2023, 2024]
    assert years.window(5) == [2020, 2021, 2022, 2023, 2024]
    assert years.window(10) == list(range(2015, 2025))
    assert years.RECOGNITION_YEAR == 2025


def test_window_ends_with_the_given_year():
    assert years.window(3, end=2025) == [2023, 2024, 2025]


def test_last_completed_year():
    assert years.last_completed_year(date(2026, 10, 18)) == 2025
    assert years.last_completed_year(date(2026, 1, 1)) == 2025
