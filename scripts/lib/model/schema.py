"""Which Table Schema describes a curated file."""

from pathlib import Path

from frictionless import Dialect, Resource, Schema, formats

from scripts.lib import paths


def schema_path(kind):
    """The Table Schema file of a kind of curated file."""
    return paths.SCHEMAS_DIR / f'{kind}.json'


def kind_of(path):
    """The kind of a curated file, which is also the name of its schema.

    A file turns `_` into `-` and loses a leading `plone-` (plone-plips-before-github.csv is a plips-before-github
    file). Raises ValueError when no schema exists for the kind.
    """
    path = Path(path)
    kind = path.stem.replace('_', '-').removeprefix('plone-')
    if not schema_path(kind).exists():
        raise ValueError(f'No schema for {path}: {schema_path(kind)} does not exist')
    return kind


class CellTypeError(ValueError):
    """A cell of a curated file cannot be read as the type its Table Schema gives it."""


def read_rows(path):
    """The rows of a curated file as plain dicts, typed by its Table Schema.

    Integers come out as int, dates as datetime.date, empty cells as None. Constraints are not validated here,
    that is the job of the checks, but a cell of the wrong type raises CellTypeError (a ValueError) instead of
    turning into None.
    Raises FileNotFoundError when the file is missing.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    schema = Schema.from_descriptor(str(schema_path(kind_of(path))))
    schema.foreign_keys = []  # they point to other files; the checks follow them, reading does not need to
    # The delimiter is stated, as in the data package: Frictionless guesses `;` for some files otherwise
    dialect = Dialect(controls=[formats.CsvControl(delimiter=',')])
    with Resource(path=str(path), schema=schema, dialect=dialect) as resource:
        rows = []
        for row in resource.read_rows():
            for error in row.errors:
                if error.type == 'type-error':
                    raise CellTypeError(f'{path}, row {row.row_number}, field {error.field_name}: '
                                        f'cannot read "{error.cell}" ({error.note})')
            rows.append(row.to_dict())
        return rows


def split_set(value):
    """The parts of a cell that holds several values separated by semicolons; () for an empty cell."""
    if value is None:
        return ()
    return tuple(part.strip() for part in value.split(';') if part.strip())
