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
    Talk,
    community_folder,
    events,
    items,
    recognition_levels,
    roles,
    talks,
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
    append_proposals,
    load_bot_accounts,
    load_excluded_repositories,
    load_registry,
    load_rejections,
)
from scripts.lib.model.sources import (  # noqa: F401
    SOURCE_KINDS,
    Source,
    archive_url_of,
    excerpt_path,
    load_sources,
    normalize_url,
    source_id,
    split_archive_url,
)
from scripts.lib.model.schema import read_rows, split_set  # noqa: F401
