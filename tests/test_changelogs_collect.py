"""The changelog collector, with a fake git layer instead of clones (#71)."""

import pytest

from scripts.collect import plone_changelogs
from scripts.lib import git_history, paths
from scripts.lib.addresses import mask_address

CHANGES = '1.0 (2009-12-01)\n----------------\n\n- Fixed the portlet [hannosch]\n'
HISTORY = 'Version 0.9\n-----------\n\n- Initial release [limi, alecm]\n'
GNU = ('2005-07-22 Hanno Schlichting <hanno@own.test>\n\n    * Fixed a test\n\n'
       '2004-07-24  Christian Heimes <chris@acme.test>\n\n    * Changed version\n')


class FakeGit:
    """The git_history functions the collector uses, with files instead of clones."""

    def __init__(self, files, branches=('master', '4.3.x', 'plip-123'), tags=None, fail=None):
        self.files = files  # {(branch, path): text}
        self.branches = list(branches)
        self.tags = tags or {}
        self.fail = fail
        self.updated = []
        self.selected = []

    def update_clone(self, url, path, token=None, tags=False):
        if self.fail and self.fail in url:
            raise git_history.GitError('fetch failed')
        self.updated.append((url, tags))

    def list_branches(self, path):
        return self.branches

    def files_at_tips(self, path, branches, select, token=None):
        self.selected.append(list(branches))
        return {(branch, file): (f'tip-{branch}', text.encode('latin-1' if 'ä' in text else 'utf-8'))
                for (branch, file), text in self.files.items() if branch in branches and select(file)}

    def tag_dates(self, path):
        return self.tags


@pytest.fixture
def fake_git(monkeypatch):
    def install(*args, **kwargs):
        fake = FakeGit(*args, **kwargs)
        for name in ('update_clone', 'list_branches', 'files_at_tips', 'tag_dates'):
            monkeypatch.setattr(git_history, name, getattr(fake, name))
        return fake
    return install


def test_default_branch_and_release_branches_at_their_tips(fake_git):
    fake = fake_git({('master', 'CHANGES.rst'): CHANGES, ('4.3.x', 'docs/HISTORY.txt'): HISTORY,
                     ('plip-123', 'CHANGES.rst'): '1.1 (2010-01-01)\n----------------\n\n- Unmerged [x]\n',
                     ('master', 'tests/CHANGES.rst'): CHANGES.replace('hannosch', 'fixture'),
                     ('master', 'docs/ChangeLog'): GNU},
                    tags={'0.9': '2008-03-01'})

    found = plone_changelogs.collect([('plone.app.x', 'master')], workers=1, log=lambda line: None)

    assert fake.updated == [('https://github.com/plone/plone.app.x.git', True)]
    # Feature branches are unmerged work
    assert fake.selected == [['master', '4.3.x']]
    assert sorted((o.branch, o.path, o.release_date, o.date_source, tuple(o.names)) for o in found) == [
        ('4.3.x', 'docs/HISTORY.txt', '2008-03-01', 'tag', ('limi', 'alecm')),
        ('master', 'CHANGES.rst', '2009-12-01', 'header', ('hannosch',)),
    ]
    assert {o.default for o in found if o.branch == 'master'} == {True}
    assert {o.commit for o in found} == {'tip-master', 'tip-4.3.x'}


def test_latin_1_files_are_read(fake_git):
    fake_git({('master', 'HISTORY.txt'): '1.0 (2004-05-01)\n----------------\n\n- Übersetzung ergänzt [jensens]\n'})

    found = plone_changelogs.collect([('Products.X', 'master')], workers=1, log=lambda line: None)

    assert [o.text for o in found] == ['Übersetzung ergänzt [jensens]']


def test_empty_repository(fake_git):
    fake_git({}, branches=[])

    assert plone_changelogs.collect([('empty', 'main')], workers=1, log=lambda line: None) == []


def test_a_failed_fetch_stops_the_collection(fake_git):
    fake_git({('master', 'CHANGES.rst'): CHANGES}, fail='broken')

    with pytest.raises(git_history.GitError):
        plone_changelogs.collect([('plone.app.x', 'master'), ('broken', 'master')], workers=2, log=lambda line: None)


@pytest.fixture
def run_main(tmp_repo, monkeypatch, fake_git):
    def run(repositories, *args, **kwargs):
        fake = fake_git(*args, **kwargs)
        monkeypatch.setattr(plone_changelogs, 'organisation_repositories', lambda session: repositories)
        monkeypatch.setattr('sys.argv', ['plone_changelogs', '--from-year', '2008', '--to-year', '2010'])
        return plone_changelogs.main(), fake
    return run


def test_main_writes_one_file_per_year(run_main, tmp_repo):
    (tmp_repo / paths.EXCLUDED_REPOSITORIES).write_text('repository,reason\nfork,Foreign history\n')
    paths.contributors_file(2009).write_text('username,total_commits\nhannosch,10\n')

    status, fake = run_main([('plone.app.x', 'master'), ('fork', 'master')],
                            {('master', 'CHANGES.rst'): CHANGES, ('4.3.x', 'docs/HISTORY.txt'): HISTORY},
                            tags={'0.9': '2008-03-01'})

    assert status == 0
    assert [url for url, _ in fake.updated] == ['https://github.com/plone/plone.app.x.git']
    assert paths.changelog_entries_file(2009).read_text().splitlines() == [
        'username,changelog_entries,repositories_count,repositories,changelog_names,matched_by',
        'hannosch,1,1,plone.app.x,hannosch,login',
    ]
    assert paths.changelog_entries_file(2008).read_text().splitlines()[1:] == [
        'alecm,1,1,plone.app.x,alecm,unmatched', 'limi,1,1,plone.app.x,limi,unmatched']
    # A year without entries gets a file with the header only
    assert paths.changelog_entries_file(2010).read_text().splitlines() == [
        'username,changelog_entries,repositories_count,repositories,changelog_names,matched_by']


def test_main_writes_nothing_when_a_fetch_fails(run_main, tmp_repo):
    status, _ = run_main([('plone.app.x', 'master'), ('broken', 'master')],
                         {('master', 'CHANGES.rst'): CHANGES}, fail='broken')

    assert status == 1
    assert not list(paths.CHANGELOGS_DIR.glob('*.csv'))


def test_year_table_masks_unmatched_addresses():
    stats = {'entries': 2, 'repositories': {'plone.app.x'}, 'names': {'jane@acme.test'}, 'layers': {'unmatched'}}

    table = plone_changelogs.year_table({'jane@acme.test': stats, 'limi': {**stats, 'names': {'limi'}}})

    masked = mask_address('jane@acme.test')
    assert masked.startswith('h-') and '@' not in masked
    assert set(table['username']) == {masked, 'limi'}
    assert set(table['changelog_names']) == {masked, 'limi'}
