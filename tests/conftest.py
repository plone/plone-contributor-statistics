import shutil
import sys
from pathlib import Path

import pytest

# The scripts run as modules from the repository root: python -m scripts.<stage>.<name>
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.lib import paths  # noqa: E402

# Header-only mapping files: the loaders require every file to exist
EMPTY_MAPPINGS = {
    paths.EXCLUDED_REPOSITORIES: 'repository,reason\n',
    paths.BOT_ACCOUNTS: 'login,reason\n',
    paths.PEOPLE: 'id,name,github,source\n',
    paths.IDENTITIES: 'person,kind,value,source\n',
    paths.AFFILIATIONS: 'person,organisation,from,to,source,checked,notes\n',
    paths.ORGANISATIONS: 'id,name,kind,aliases,notes\n',
    paths.AFFILIATION_PROPOSALS: 'person,organisation,from,to,evidence\n',
}


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """An empty repository in tmp_path, as the current directory, with the folders and empty mapping files."""
    monkeypatch.chdir(tmp_path)
    for name, value in vars(paths).items():
        if isinstance(value, Path) and name.isupper():
            (value if not value.suffix else value.parent).mkdir(parents=True, exist_ok=True)
    for path, header in EMPTY_MAPPINGS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(header, encoding='utf-8')
    # The registers are read through their schemas
    shutil.copytree(REPO / 'curated/schemas', tmp_path / 'curated/schemas', dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def schemas(tmp_repo):
    """The real schemas of the registers, copied into the empty repository."""
    shutil.copytree(REPO / 'curated/schemas', tmp_repo / 'curated/schemas', dirs_exist_ok=True)
    return tmp_repo


@pytest.fixture
def write_registers(schemas):
    """A function writing the people, affiliations and organisations registers from the given rows."""
    source = 'https://example.org/record'

    def write(people=(), affiliations=(), organisations=()):
        """people: (id, github); affiliations: (person, organisation id, from, to); organisations: (id, name)."""
        paths.PEOPLE.write_text('id,name,github,source\n' + ''.join(
            f'{i},{i},{github},{source}\n' for i, github in people), encoding='utf-8')
        paths.AFFILIATIONS.write_text('person,organisation,from,to,source,checked,notes\n' + ''.join(
            f'{person},{org},{start},{end},{source},,\n' for person, org, start, end in affiliations),
            encoding='utf-8')
        paths.ORGANISATIONS.write_text('id,name,kind,aliases,notes\n' + ''.join(
            f'{i},{name},organisation,,\n' for i, name in organisations), encoding='utf-8')

    return write
