import shutil
import sys
from pathlib import Path

import pytest

# The scripts run as modules from the repository root: python -m scripts.<stage>.<name>
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.lib import paths  # noqa: E402

# Header-only registers and lists: the loaders require every file to exist
EMPTY_MAPPINGS = {
    paths.EXCLUDED_REPOSITORIES: 'repository,reason\n',
    paths.BOT_ACCOUNTS: 'login,reason\n',
    paths.PEOPLE: 'id,name\n',
    paths.IDENTITIES: 'person,kind,value,source,snippet,notes\n',
    paths.AFFILIATIONS: 'id,person,organisation,from,to,status,checked,notes\n',
    paths.CITATIONS: 'affiliation,source,snippet,supersedes,notes\n',
    paths.ORGANISATIONS: 'id,name,kind,github,aliases,notes\n',
    paths.SOURCES: 'id,kind,title,date,url,archive_url,fetched,notes\n',
}


@pytest.fixture(autouse=True)
def private_cache(tmp_path_factory, monkeypatch):
    """Every test gets its own cache directory: no test reads or writes the cache of the real checkout."""
    monkeypatch.setenv('PLONE_STATS_CACHE', str(tmp_path_factory.mktemp('cache')))


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """An empty repository in tmp_path, as the current directory, with the folders and empty registers."""
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


RECORD = 'https://example.org/record'


def record_source(url=RECORD):
    """Add a page of the url to the source register of the current directory, with a passage; its id."""
    from scripts.lib.model.sources import source_id

    sid = source_id(url)
    rows = paths.SOURCES.read_text(encoding='utf-8')
    if f'\n{sid},' not in rows:
        lines = rows.splitlines(keepends=True)
        lines.append(f'{sid},page,A record,2026-01-01,{url},,2026-10-22T10:00:00Z,\n')
        paths.SOURCES.write_text(lines[0] + ''.join(sorted(lines[1:])), encoding='utf-8')
        (paths.EXCERPTS_DIR / f'{sid}.md').write_text('A record.\n', encoding='utf-8')
    return sid


@pytest.fixture
def write_registers(tmp_repo):
    """A function writing the people, identities, affiliations, citations and organisations registers."""
    from scripts.lib.model import affiliation_id

    def write(people=(), affiliations=(), organisations=()):
        """people: (id, github); affiliations: (person, organisation id, from, to); organisations: (id, name).

        A person with a login gets a `github` identity; every identity and affiliation cites one record.
        """
        sid = record_source()
        paths.PEOPLE.write_text('id,name\n' + ''.join(f'{i},{i}\n' for i, _ in sorted(people)), encoding='utf-8')
        paths.IDENTITIES.write_text('person,kind,value,source,snippet,notes\n' + ''.join(
            f'{i},github,{github},{sid},,\n' for i, github in sorted(people) if github), encoding='utf-8')
        rows = [(affiliation_id(person, org, start, end), person, org, start, end)
                for person, org, start, end in affiliations]
        paths.AFFILIATIONS.write_text('id,person,organisation,from,to,status,checked,notes\n' + ''.join(
            f'{aid},{person},{org},{start},{"" if end is None else end},stated,,\n'
            for aid, person, org, start, end in rows), encoding='utf-8')
        paths.CITATIONS.write_text('affiliation,source,snippet,supersedes,notes\n' + ''.join(
            f'{aid},{sid},,,\n' for aid, *_ in sorted(rows)), encoding='utf-8')
        paths.ORGANISATIONS.write_text('id,name,kind,github,aliases,notes\n' + ''.join(
            f'{i},{name},organisation,,,\n' for i, name in organisations), encoding='utf-8')

    return write


def registry_of(people, identities=(), affiliations=(), organisations=()):
    """A Registry of people given as (id, name, GitHub login or None, source) and of the other rows.

    A person with a login gets a `github` identity citing the source.
    """
    from scripts.lib.model import Identity, Person, Registry

    logins = [Identity(pid, 'github', github, source) for pid, _, github, source in people if github]
    return Registry([Person(pid, name) for pid, name, _, _ in people], [*logins, *identities], affiliations,
                    organisations)
