"""The community page doesn't use real people as examples."""

import re
from pathlib import Path

from scripts.lib.model import LOGIN_KINDS, load_registry

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = sorted((ROOT / 'scripts/report/site').rglob('*.html'))


def logins():
    """Every GitHub login the register knows: the people's own and their second accounts."""
    registry = load_registry(ROOT / 'curated/mappings')
    return {identity.value.casefold() for identity in registry.identities if identity.kind in LOGIN_KINDS}


def test_placeholders_name_no_person():
    known = logins()
    for path in TEMPLATES:
        for placeholder in re.findall(r'placeholder="([^"]*)"', path.read_text(encoding='utf-8')):
            words = {word.casefold() for word in re.findall(r'[\w-]+', placeholder)}
            assert not words & known, f'{path.name}: a real login as an example: {placeholder!r}'
