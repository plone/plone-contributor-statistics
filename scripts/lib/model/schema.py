"""Which Table Schema describes a curated file."""

import re
from pathlib import Path

from frictionless import Resource, Schema

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


def read_rows(path):
    """The rows of a curated file as plain dicts, typed by its Table Schema.

    Integers come out as int, dates as datetime.date, empty cells as None. Constraints are not validated here,
    that is the job of the checks. Raises FileNotFoundError when the file is missing.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    schema = Schema.from_descriptor(str(schema_path(kind_of(path))))
    schema.foreign_keys = []  # they point to other files; the checks follow them, reading does not need to
    with Resource(path=str(path), schema=schema) as resource:
        return [row.to_dict() for row in resource.read_rows()]


def split_set(value):
    """The parts of a cell that holds several values separated by semicolons; () for an empty cell."""
    if value is None:
        return ()
    return tuple(part.strip() for part in value.split(';') if part.strip())
