"""The community page doesn't use real people as examples."""

import csv
import re
from pathlib import Path

from scripts.lib import paths

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = sorted((ROOT / 'scripts/report/site').rglob('*.html'))


def logins():
    with open(ROOT / paths.ORGANISATIONS, newline='', encoding='utf-8') as f:
        return {login.casefold() for row in csv.DictReader(f) for login in (row['Team'] or '').split(';') if login}


def test_placeholders_name_no_person():
    known = logins()
    for path in TEMPLATES:
        for placeholder in re.findall(r'placeholder="([^"]*)"', path.read_text(encoding='utf-8')):
            words = {word.casefold() for word in re.findall(r'[\w-]+', placeholder)}
            assert not words & known, f'{path.name}: a real login as an example: {placeholder!r}'
