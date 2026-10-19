"""The model library: the registers of people and organisations, and reading curated files through their schema."""

from scripts.lib.model.community import (  # noqa: F401
    EVENT_KINDS,
    IN_PERSON,
    MIN_EPISODES,
    ROLE_KINDS,
    TALK_TYPES,
    Event,
    Item,
    Role,
    community_folder,
    events,
    items,
    roles,
)
from scripts.lib.model.registers import (  # noqa: F401
    MAPPINGS_DIR,
    UNMAPPED,
    Affiliation,
    Identity,
    Organisation,
    Person,
    Registry,
    append_person,
    load_bot_accounts,
    load_excluded_repositories,
    load_registry,
)
from scripts.lib.model.schema import read_rows, split_set  # noqa: F401
