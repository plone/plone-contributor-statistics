"""The model library: the registers of people and organisations, and reading curated files through their schema."""

from scripts.lib.model.registers import (  # noqa: F401
    UNMAPPED,
    Affiliation,
    Identity,
    Organisation,
    Person,
    Registry,
    load_bot_accounts,
    load_excluded_repositories,
    load_registry,
)
from scripts.lib.model.schema import read_rows, split_set  # noqa: F401
