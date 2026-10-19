"""Which Table Schema describes a curated file."""

import re
from pathlib import Path

from scripts.lib import paths


def schema_path(kind):
    """The Table Schema file of a kind of curated file."""
    return paths.SCHEMAS_DIR / f'{kind}.json'


def kind_of(path):
    """The kind of a curated file, which is also the name of its schema.

    Community files lose the year (2023-sprints.csv is a sprints file); other files turn `_` into `-`
    and lose a leading `plone-`. Raises ValueError when no schema exists for the kind.
    """
    path = Path(path)
    if paths.COMMUNITY.name in path.parts:
        kind = re.sub(r'^\d{4}-', '', path.stem)
    else:
        kind = path.stem.replace('_', '-')
        kind = kind.removeprefix('plone-')
    if not schema_path(kind).exists():
        raise ValueError(f'No schema for {path}: {schema_path(kind)} does not exist')
    return kind
