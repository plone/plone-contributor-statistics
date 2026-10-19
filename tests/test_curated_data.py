"""The curated data passes the schemas and the custom checks, so that `make test` runs the checks."""

import pytest

from scripts.tools import check


@pytest.mark.xfail(strict=True, reason='until the migration lands (#139)')
def test_curated_data_passes_the_checks():
    assert check.validate() == []
