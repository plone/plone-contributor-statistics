"""The curated data passes the schemas and the custom checks, so that `make test` runs the checks."""

from scripts.tools import check


def test_curated_data_passes_the_checks():
    assert check.validate() == []
