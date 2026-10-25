import csv
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


# The columns of the community files, as the schemas give them
COMMUNITY_COLUMNS = {
    'events': 'id,kind,name,year,start,end,location,format,level,sources,cited_as,notes',
    'talks': 'id,event,type,title,speakers,organisations,location,video,sources,cited_as,notes',
    'trainings': 'id,event,title,trainers,sources,cited_as,notes',
    'organisers': 'event,person,organisation,sources,cited_as,notes',
    'board-of-directors': 'year,person,role,sources,cited_as,notes',
    'team-leaders': 'year,person,team,sources,cited_as,notes',
    'release-managers': 'year,person,sources,cited_as,notes',
    'podcasts': 'year,series,person,episodes,sources,cited_as,notes',
}
# The id prefixes of the rows that have opaque ids
ID_PREFIXES = {'talks': 't', 'trainings': 'r'}


def community_rows(name, *rows, folder=None):
    """Add rows to a community file of the current directory (or of the folder); the file gets its header first.

    name: events, talks, trainings, organisers or a roles file (board-of-directors, team-leaders, release-managers,
    podcasts). A row is a dict of cells; a missing cell is empty, and a talk or training without an id gets one.
    """
    path = Path(folder or paths.COMMUNITY) / f'{name}.csv'
    columns = COMMUNITY_COLUMNS[name].split(',')
    new = not path.exists()
    count = 0 if new else len(path.read_text(encoding='utf-8').splitlines()) - 1
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator='\n')
        if new:
            writer.writeheader()
        for n, row in enumerate(rows, start=count + 1):
            unknown = set(row) - set(columns)
            assert not unknown, f'{name} has no column {sorted(unknown)}'
            if name in ID_PREFIXES and 'id' not in row:
                row = {**row, 'id': f'{ID_PREFIXES[name]}{n:08x}'}
            writer.writerow({column: row.get(column, '') for column in columns})
    return path


def community_event(id, kind, year, organisers=(), organisations=(), cited_as=RECORD, folder=None, **cells):
    """Add an event to the events file, and its organisers, people first, with the event's citation.

    kind: conference, symposium, wpd or sprint; the name is the id unless given.
    """
    community_rows('events', {'id': id, 'kind': kind, 'name': cells.pop('name', id), 'year': year,
                              'cited_as': cited_as, **cells}, folder=folder)
    named = [{'person': person} for person in organisers] + [{'organisation': o} for o in organisations]
    if named:
        community_rows('organisers', *({'event': id, 'cited_as': cited_as, **n} for n in named), folder=folder)
    return id


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
