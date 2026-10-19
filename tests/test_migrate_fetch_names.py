import csv
from datetime import date

from scripts.lib import paths
from scripts.tools import migrate_data_structure as migrate


def _old_structure():
    paths.ORGANISATIONS.write_text('Organisation,Team\nAcme,pbauer;tisto\n', encoding='utf-8')
    paths.OVERRIDES.write_text('github_username,organisation,from_year,to_year,source\n', encoding='utf-8')
    paths.FULLNAMES.write_text(
        'github username,fullname,source\npbauer,Philip Bauer,https://github.com/pbauer\n', encoding='utf-8')


def test_logins_without_a_name_skips_named_logins(tmp_repo):
    _old_structure()
    assert migrate.logins_without_a_name(tmp_repo) == {'tisto'}


def test_logins_without_a_name_skips_handles_and_commit_author_names(tmp_repo):
    _old_structure()
    paths.ORGANISATIONS.write_text('Organisation,Team\nAcme,pbauer;tisto;handle1;mrx;hidden\n', encoding='utf-8')
    paths.COMMIT_AUTHORS.write_text(
        'email,github_username,name,source\nx@example.org,mrx,Mister X,svn\ny@example.org,hidden,,svn\n',
        encoding='utf-8')
    (paths.COMMUNITY / '2020-release-managers.csv').write_text(
        'Name,Github\nSome Body,handle1\n', encoding='utf-8')
    assert migrate.logins_without_a_name(tmp_repo) == {'tisto', 'hidden'}


def test_logins_without_a_name_include_proposal_logins(tmp_repo):
    # The migration makes a person of every login of the old proposals file, so it needs their names too
    _old_structure()
    paths.COMMIT_AUTHORS.write_text('email,github_username,name,source\nd@example.org,,Dee Veeze,svn\n',
                                    encoding='utf-8')
    paths.PROPOSALS.write_text('contributor,organisation,from_year,to_year,evidence\n'
                               'albertcasado,Onna,2018,2018,x\nDee Veeze,Zest,2016,2017,x\n', encoding='utf-8')
    assert migrate.logins_without_a_name(tmp_repo) == {'tisto', 'albertcasado'}


def test_write_profile_names_uses_login_when_profile_has_no_name(tmp_path):
    path = tmp_path / 'profile_names.csv'
    migrate.write_profile_names({'tisto': 'Timo Stollenwerk', 'nobody': ''}, path)
    rows = list(csv.DictReader(path.open(encoding='utf-8')))
    today = date.today().isoformat()
    assert rows == [{'login': 'nobody', 'name': 'nobody', 'fetched': today},
                    {'login': 'tisto', 'name': 'Timo Stollenwerk', 'fetched': today}]


def test_fetch_names_main_writes_file(tmp_repo, monkeypatch):
    _old_structure()
    monkeypatch.setenv('GITHUB_TOKEN', 'secret')
    calls = []

    def fake(session, logins, batch=50):
        calls.append((session.headers['Authorization'], list(logins)))
        return {'tisto': 'Timo Stollenwerk'}

    monkeypatch.setattr(migrate, 'fetch_profile_names', fake)
    path = tmp_repo / 'out' / 'profile_names.csv'
    migrate.main(['fetch-names', '--out', str(path)])
    assert calls == [('token secret', ['tisto'])]
    rows = list(csv.DictReader(path.open(encoding='utf-8')))
    assert rows == [{'login': 'tisto', 'name': 'Timo Stollenwerk', 'fetched': date.today().isoformat()}]
