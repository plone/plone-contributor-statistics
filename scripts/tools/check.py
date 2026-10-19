"""Validate the curated data package: the Table Schemas and the custom checks.

Run from the repository root: python -m scripts.tools.check
Prints one line per error as file:row:field: message, and exits 1 when there are errors.
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

from frictionless import Checklist, Package

from scripts.lib import paths
from scripts.lib.model.checks import checks_for

NEAREST = 3


def validate(root=Path('.')):
    """Every error of the package as (file relative to root, row number, field name, message).

    Each resource is validated as part of the package, so Frictionless resolves its foreign keys,
    together with the custom checks of that resource.
    """
    package = Package(str(Path(root) / paths.DATAPACKAGE))
    found = []
    for resource in package.resources:
        report = resource.validate(checklist=Checklist(checks=checks_for(resource.name, package)))
        file = (paths.DATAPACKAGE.parent / resource.path).as_posix()
        for task in report.tasks:
            for error in task.errors:
                row = getattr(error, 'row_number', None)
                field = getattr(error, 'field_name', None) or next(iter(getattr(error, 'field_names', [])), None)
                message = error.message + _hint(error, resource, package)
                found.append((file, row, field, message))
    return found


def _hint(error, resource, package):
    """`  nearest: a, b, c` for a key that is not in its register, else an empty text."""
    if error.type == 'foreign-key':
        register = error.reference_name or resource.name
        values = error.field_cells[:1]
    elif error.type == 'set-keys':
        field = resource.schema.get_field(error.field_name)
        register = field.to_descriptor().get('x-set')
        values = re.findall(r'"([^"]+)" is not in the register', error.note)
    else:
        return ''
    if not register or not values:
        return ''
    reference = package.get_resource(register)
    key = reference.schema.primary_key[0]
    ids = [row[key] for row in reference.read_rows() if row[key]]
    close = difflib.get_close_matches(values[0], ids, n=NEAREST)
    return f'  nearest: {", ".join(close)}' if close else ''


def main(argv=None):
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    errors = validate()
    for file, row, field, message in errors:
        print(f'{file}:{row or ""}:{field or ""}: {message}')
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
