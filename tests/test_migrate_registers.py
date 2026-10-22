"""The migration of the registers to citations (plan 2c): pure functions on small fixtures, and the command."""

import csv
import hashlib
import json
from datetime import UTC, datetime

from scripts.lib import paths
from scripts.lib.model import load_sources, read_excerpt
from scripts.lib.model.sources import source_id
from scripts.tools import migrate_registers
from scripts.tools.migrate_registers import affiliation_id, migrate

NOW = datetime(2026, 10, 22, 18, 0, tzinfo=UTC)
PAGE = 'https://acme.example/team'
ARCHIVED = 'https://web.archive.org/web/20101010101010/https://acme.example/team'
PROFILE = 'https://github.com/janedoe'
SEARCH = 'https://github.com/search?q=author%3Ajanedoe+org%3Aacme+committer-date%3A2014-01-01..2014-12-31&type=commits'
COMMIT = 'https://github.com/acme/thing/commit/abc123'


def person(id, name, github='', source=PROFILE):
    return {'id': id, 'name': name, 'github': github, 'source': source}


def affiliation(person, organisation, start, end='', source=PAGE, checked='2026-10-18', notes=''):
    return {'person': person, 'organisation': organisation, 'from': str(start), 'to': str(end), 'source': source,
            'checked': checked, 'notes': notes}


def result(url, sid=None, error=None):
    return {'url': url, 'source_id': sid, 'created': bool(sid), 'added': [], 'missing': [], 'unreachable': False,
            'error': error}


def run(people=(), identities=(), affiliations=(), rejections=(), results=(), searches=None, worklist=(),
        excerpts=None, kinds=None):
    """migrate() on the rows; `excerpts` {source id: text} are the captured sources, `kinds` their kinds."""
    excerpts = excerpts or {}
    kinds = kinds or {}
    sources = {sid: {'id': sid, 'kind': kinds.get(sid, 'page'), 'url': '', 'archive_url': ''} for sid in excerpts}
    return migrate(list(people), list(identities), list(affiliations), list(rejections), list(results),
                   searches or {}, list(worklist), sources, lambda sid: excerpts.get(sid, ''), now=NOW)


def citations_of(migrated, affiliation_row=None):
    if affiliation_row is None:
        return migrated.citations
    return [c for c in migrated.citations if c['affiliation'] == affiliation_row['id']]


def test_people_lose_github_and_source():
    migrated = run(people=[person('jane-doe', 'Jane Doe', 'janedoe')], results=[result(PROFILE, 'p1')],
                   excerpts={'p1': 'Login: janedoe'})
    assert migrated.people == [{'id': 'jane-doe', 'name': 'Jane Doe'}]


def test_people_github_becomes_github_identity():
    cell = f'"Jane Doe works at Acme", GitHub profile: {PROFILE}'
    migrated = run(people=[person('jane-doe', 'Jane Doe', 'janedoe', cell)], results=[result(PROFILE, 'p1')],
                   excerpts={'p1': 'Login: janedoe\n\nJane Doe works at Acme since 2010.'})
    assert migrated.identities == [{'person': 'jane-doe', 'kind': 'github', 'value': 'janedoe', 'source': 'p1',
                                    'snippet': 'Jane Doe works at Acme', 'notes': cell}]


def test_login_identity_without_people_github_stays_alias():
    # The username stays person:<id>: a second account never becomes the main one
    login = {'person': 'jane-doe', 'kind': 'login', 'value': 'jdoe2',
             'source': f'GitHub links her address to this account: {COMMIT}'}
    migrated = run(people=[person('jane-doe', 'Jane Doe')], identities=[login],
                   results=[result(PROFILE, 'p1'), result(COMMIT, 'c1')], excerpts={'p1': 'x', 'c1': 'y'})
    kinds = {(i['kind'], i['value']) for i in migrated.identities}
    assert ('github-alias', 'jdoe2') in kinds
    assert not any(kind == 'github' for kind, _ in kinds)


def test_login_identity_of_a_person_with_github_becomes_alias():
    login = {'person': 'jane-doe', 'kind': 'login', 'value': 'jdoe2', 'source': COMMIT}
    migrated = run(people=[person('jane-doe', 'Jane Doe', 'janedoe')], identities=[login],
                   results=[result(PROFILE, 'p1'), result(COMMIT, 'c1')], excerpts={'p1': 'x', 'c1': 'y'})
    assert [(i['kind'], i['value']) for i in migrated.identities] == [('github', 'janedoe'), ('github-alias', 'jdoe2')]


def test_person_without_github_gets_name_identity():
    cell = f'"Jane Doe, Acme", speaker page: {PAGE}'
    migrated = run(people=[person('jane-doe', 'Jane Doe', '', cell)], results=[result(PAGE, 's1')],
                   excerpts={'s1': 'Jane Doe, Acme. She talks.'})
    assert migrated.identities == [{'person': 'jane-doe', 'kind': 'name', 'value': 'Jane Doe', 'source': 's1',
                                    'snippet': 'Jane Doe, Acme', 'notes': cell}]


def test_identity_cell_kept_in_notes():
    # The first captured address is the source; the email address is the snippet when the excerpt holds it
    lost = 'https://lost.example/page'
    cell = f'Same name in commits: {lost}; example commit: {COMMIT}'
    email = {'person': 'jane-doe', 'kind': 'email', 'value': 'jane@acme.example', 'source': cell}
    migrated = run(people=[person('jane-doe', 'Jane Doe', 'janedoe')], identities=[email],
                   results=[result(PROFILE, 'p1'), result(lost), result(COMMIT, 'c1')],
                   excerpts={'p1': 'x', 'c1': 'Author: Jane Doe <jane@acme.example>'})
    row = next(i for i in migrated.identities if i['kind'] == 'email')
    assert row == {'person': 'jane-doe', 'kind': 'email', 'value': 'jane@acme.example', 'source': 'c1',
                   'snippet': 'jane@acme.example', 'notes': cell}


def test_identity_without_captured_address_cites_an_uncaptured_source():
    lost = 'https://lost.example/page'
    migrated = run(people=[person('jane-doe', 'Jane Doe', '', f'record: {lost}')], results=[result(lost)])
    assert migrated.identities[0]['source'] == source_id(lost)
    assert [row['id'] for row in migrated.new_sources] == [source_id(lost)]


def test_snippet_only_where_verified():
    # The quote is in the archived copy only: the live page gets no snippet
    row = affiliation('jane-doe', 'acme', 2010, 2012,
                      source=f'"Jane Doe, developer", team page: {PAGE} (archived: {ARCHIVED})')
    migrated = run(people=[person('jane-doe', 'Jane Doe', 'janedoe')], affiliations=[row],
                   results=[result(PROFILE, 'p1'), result(PAGE, 'live'), result(ARCHIVED, 'old')],
                   excerpts={'p1': 'x', 'live': 'Our team: John Smith', 'old': 'Our team: Jane Doe, developer'})
    aid = affiliation_id('jane-doe', 'acme', '2010', '2012')
    assert citations_of(migrated) == [
        {'affiliation': aid, 'source': 'live', 'snippet': '', 'supersedes': '',
         'notes': 'label: team page; not found: "Jane Doe, developer"'},
        {'affiliation': aid, 'source': 'old', 'snippet': 'Jane Doe, developer', 'supersedes': '',
         'notes': 'label: team page'},
    ]


def test_citation_per_snippet_and_label_in_notes():
    row = affiliation('jane-doe', 'acme', 2010, source=f'"Jane Doe", "Acme team", team page: {PAGE}')
    migrated = run(affiliations=[row], results=[result(PAGE, 's1')],
                   excerpts={'s1': 'The Acme team.\n\nJane Doe joined.'})
    assert [(c['source'], c['snippet'], c['notes']) for c in migrated.citations] == [
        ('s1', 'Acme team', 'label: team page'), ('s1', 'Jane Doe', 'label: team page')]


def test_unverified_quote_kept_in_notes():
    # A quote of another segment stays out of a citation that never claimed it, unless no address holds it
    other = 'https://other.example/about'
    cell = f'listed on the team page: {PAGE}; "Two of our developers (Jane Doe)", about page: {other}'
    row = affiliation('jane-doe', 'acme', 2010, source=cell)
    found = run(affiliations=[row], results=[result(PAGE, 's1'), result(other, 's2')],
                excerpts={'s1': 'Team', 's2': 'Two of our developers (Jane Doe) build sites.'})
    assert [(c['source'], c['snippet'], c['notes']) for c in found.citations] == [
        ('s1', '', 'label: listed on the team page'),
        ('s2', 'Two of our developers (Jane Doe)', 'label: about page')]
    lost = run(affiliations=[row], results=[result(PAGE, 's1'), result(other, 's2')],
               excerpts={'s1': 'Team', 's2': 'Nothing'})
    assert [(c['source'], c['notes']) for c in lost.citations] == [
        ('s1', 'label: listed on the team page'),
        ('s2', 'label: about page; not found: "Two of our developers (Jane Doe)"')]
    homeless = affiliation('jane-doe', 'acme', 2010, source=f'team page: {PAGE}; "Jane Doe at Acme"')
    lost = run(affiliations=[homeless], results=[result(PAGE, 's1')], excerpts={'s1': 'Team'})
    assert [c['notes'] for c in lost.citations] == ['label: team page; not found: "Jane Doe at Acme"']


def test_notes_cell_is_cited_and_kept():
    notes = f'confirmed by her: {COMMIT}'
    row = affiliation('jane-doe', 'acme', 2010, notes=notes)
    migrated = run(affiliations=[row], results=[result(PAGE, 's1'), result(COMMIT, 'c1')],
                   excerpts={'s1': 'x', 'c1': 'y'})
    assert migrated.affiliations[0]['notes'] == notes
    assert [(c['source'], c['notes']) for c in migrated.citations] == [('c1', 'label: confirmed by her'),
                                                                       ('s1', '')]


def test_uncaptured_url_becomes_a_source():
    video = 'https://www.youtube.com/watch?v=abc'
    rows = [affiliation('jane-doe', 'acme', 2010, 2011, source=f'talk: {video}; team page: {ARCHIVED}'),
            affiliation('jane-doe', 'acme', 2012, source=f'talk: {video}')]
    migrated = run(affiliations=rows,
                   results=[result(video, error=f'{video}: yt-dlp failed for {video}\nHTTP Error 429'),
                            result(ARCHIVED)],
                   worklist=[{'url': video, 'quotes': [], 'names': [], 'kind': 'video'}])
    video_id = source_id(video)
    archived_id = source_id('https://acme.example/team', '20101010101010')
    expected = [
        {'id': archived_id, 'kind': 'page', 'title': ARCHIVED, 'date': '2026-10-22',
         'url': 'https://acme.example/team', 'archive_url': ARCHIVED, 'fetched': '2026-10-22T18:00:00Z',
         'notes': 'not captured on 2026-10-22: nothing found'},
        {'id': video_id, 'kind': 'video', 'title': video, 'date': '2026-10-22', 'url': video, 'archive_url': '',
         'fetched': '2026-10-22T18:00:00Z', 'notes': f'not captured on 2026-10-22: yt-dlp failed for {video}'},
    ]
    assert migrated.new_sources == sorted(expected, key=lambda row: row['id'])
    assert migrated.new_excerpts[video_id] == f'not captured on 2026-10-22: yt-dlp failed for {video}'
    assert migrated.new_excerpts[archived_id] == 'not captured on 2026-10-22: nothing found'
    assert sorted(c['source'] for c in migrated.citations) == sorted([video_id, archived_id, video_id])


def test_search_url_cited_through_its_commits():
    other = 'https://github.com/acme/thing/commit/def456'
    empty = SEARCH.replace('2014', '2015')
    row = affiliation('jane-doe', 'acme', 2014, 2015, source=f'commits in @acme: {SEARCH}; and 2015: {empty}')
    migrated = run(affiliations=[row], searches={SEARCH: [COMMIT, other], empty: []},
                   results=[result(COMMIT, 'c1'), result(other, 'c2')], excerpts={'c1': 'x', 'c2': 'y'})
    assert [(c['source'], c['notes']) for c in migrated.citations] == [
        ('c1', f'label: commits in @acme; search: {SEARCH}; label: and 2015; search without results: {empty}'),
        ('c2', f'label: commits in @acme; search: {SEARCH}')]
    assert migrated.new_sources == []


def test_search_without_results_alone_cites_the_search():
    row = affiliation('jane-doe', 'acme', 2014, source=f'commits in @acme: {SEARCH}')
    migrated = run(affiliations=[row], searches={SEARCH: []})
    assert [(c['source'], c['notes']) for c in migrated.citations] == [
        (source_id(SEARCH), f'label: commits in @acme; search without results: {SEARCH}')]
    assert migrated.new_sources[0]['notes'] == 'not captured on 2026-10-22: nothing found'


def test_not_verified_rows_are_assumed():
    rows = [affiliation('jane-doe', 'acme', 2010, 2011),
            affiliation('jane-doe', 'acme', 2012, notes='range from the current entry; not verified (#139)')]
    migrated = run(affiliations=rows, results=[result(PAGE, 's1')], excerpts={'s1': 'x'})
    assert [(a['from'], a['status']) for a in migrated.affiliations] == [('2010', 'stated'), ('2012', 'assumed')]


def test_rejection_becomes_denied_with_decision_source():
    decision = 'https://github.com/plone/plone-contributor-statistics/pull/153#issuecomment-1'
    evidence = 'http://web.archive.org/web/20071024104004/http://www.jarn.com:80/about/team'
    rejections = [
        {'person': 'jane-doe', 'organisation': 'zest', 'from': '2024', 'to': '2025',
         'reason': 'an old mailbox', 'source': decision},
        {'person': 'jane-doe', 'organisation': 'beta', 'from': '2009', 'to': '2009',
         'reason': 'contract work for a client', 'source': f'listed on the team page: {evidence}'},
    ]
    migrated = run(rejections=rejections, results=[result(decision, 'd1'), result(evidence, 'e1')],
                   excerpts={'d1': 'Zest: an old mailbox, deny.', 'e1': 'Team'}, kinds={'d1': 'issue-comment'})
    denied = {a['organisation']: a for a in migrated.affiliations}
    assert denied['zest'] == {'id': affiliation_id('jane-doe', 'zest', '2024', '2025'), 'person': 'jane-doe',
                              'organisation': 'zest', 'from': '2024', 'to': '2025', 'status': 'denied',
                              'checked': '', 'notes': 'an old mailbox'}
    assert denied['beta']['status'] == 'denied'
    assert [(c['source'], c['snippet']) for c in citations_of(migrated, denied['zest'])] == [('d1', 'an old mailbox')]
    assert [(c['source'], c['notes']) for c in citations_of(migrated, denied['beta'])] == [
        ('e1', 'label: listed on the team page')]
    assert migrated.kind_updates == {'d1': 'decision'}


def test_uncaptured_decision_source_is_a_decision():
    decision = 'https://github.com/plone/plone-contributor-statistics/pull/90'
    rejection = {'person': 'jane-doe', 'organisation': 'beta', 'from': '2023', 'to': '2023',
                 'reason': 'did no Plone projects', 'source': decision}
    migrated = run(rejections=[rejection], results=[result(decision)])
    assert [(row['id'], row['kind']) for row in migrated.new_sources] == [(source_id(decision), 'decision')]
    assert migrated.kind_updates == {}
    assert migrated.citations[0]['snippet'] == ''


def test_affiliation_id_is_stable():
    expected = 'a' + hashlib.sha1('jane-doe|acme|2010|'.encode()).hexdigest()[:8]
    assert affiliation_id('jane-doe', 'acme', '2010', '') == expected
    migrated = run(affiliations=[affiliation('jane-doe', 'acme', 2010)], results=[result(PAGE, 's1')],
                   excerpts={'s1': 'x'})
    assert migrated.affiliations[0]['id'] == expected
    assert migrated.citations[0]['affiliation'] == expected


def test_output_is_sorted():
    other = 'https://other.example/'
    people = [person('zoe', 'Zoe Z', 'zoe'), person('adam', 'Adam A', '')]
    identities = [{'person': 'zoe', 'kind': 'email', 'value': 'b@x.example', 'source': PROFILE},
                  {'person': 'zoe', 'kind': 'email', 'value': 'a@x.example', 'source': PROFILE},
                  {'person': 'adam', 'kind': 'name', 'value': 'A. A.', 'source': PROFILE}]
    affiliations = [affiliation('zoe', 'beta', 2012), affiliation('zoe', 'acme', 2012, 2012, source=other),
                    affiliation('zoe', 'acme', 2010, 2011), affiliation('adam', 'acme', 2020)]
    migrated = run(people, identities, affiliations, results=[result(PROFILE, 'p1'), result(PAGE, 's2'),
                                                              result(other, 's1')],
                   excerpts={'p1': 'x', 's1': 'y', 's2': 'z'})
    assert [p['id'] for p in migrated.people] == ['adam', 'zoe']
    assert [(i['person'], i['kind'], i['value']) for i in migrated.identities] == [
        ('adam', 'name', 'A. A.'), ('adam', 'name', 'Adam A'), ('zoe', 'email', 'a@x.example'),
        ('zoe', 'email', 'b@x.example'), ('zoe', 'github', 'zoe')]
    assert [(a['person'], a['from'], a['organisation']) for a in migrated.affiliations] == [
        ('adam', '2020', 'acme'), ('zoe', '2010', 'acme'), ('zoe', '2012', 'acme'), ('zoe', '2012', 'beta')]
    keys = [(c['affiliation'], c['source'], c['snippet']) for c in migrated.citations]
    assert keys == sorted(keys)


def test_summary_counts():
    row = affiliation('jane-doe', 'acme', 2010, source=f'"Jane Doe", team page: {PAGE}; talk: {COMMIT}')
    migrated = run(people=[person('jane-doe', 'Jane Doe', 'janedoe')], affiliations=[row],
                   results=[result(PROFILE, 'p1'), result(PAGE, 's1'), result(COMMIT)],
                   excerpts={'p1': 'x', 's1': 'Jane Doe'})
    text = migrate_registers.summary(migrated)
    assert 'people: 1' in text and 'affiliations: 1' in text and 'citations: 2' in text
    assert 'uncaptured sources created: 1' in text
    assert 'citations with a snippet: 1, without: 1' in text
    assert 'kind updates: 0' in text


def _write_csv(path, rows, fields):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def _old_repository(tmp_repo):
    """The old registers and the files of plan 2a in the temporary repository."""
    _write_csv(paths.PEOPLE, [person('jane-doe', 'Jane Doe', 'janedoe')], ['id', 'name', 'github', 'source'])
    _write_csv(paths.AFFILIATIONS, [affiliation('jane-doe', 'acme', 2010)],
               ['person', 'organisation', 'from', 'to', 'source', 'checked', 'notes'])
    archive = tmp_repo / 'archive/migration-to-sources'
    archive.mkdir(parents=True)
    (archive / 'capture-results.jsonl').write_text(
        ''.join(json.dumps(line) + '\n' for line in [result(PROFILE, 'aaaaaaaaaaaa'), result(PAGE)]),
        encoding='utf-8')
    (archive / 'searches.json').write_text('{}\n', encoding='utf-8')
    (archive / 'worklist.jsonl').write_text('', encoding='utf-8')
    paths.SOURCES.write_text('id,kind,title,date,url,archive_url,fetched,notes\n'
                             f'aaaaaaaaaaaa,profile,Jane,2026-10-22,{PROFILE},,2026-10-22T15:00:00Z,\n',
                             encoding='utf-8')


def test_command_without_write_changes_nothing(tmp_repo, capsys):
    _old_repository(tmp_repo)
    before = {path: path.read_text(encoding='utf-8') for path in tmp_repo.rglob('*') if path.is_file()}
    assert migrate_registers.main([]) == 0
    assert {path: path.read_text(encoding='utf-8') for path in tmp_repo.rglob('*') if path.is_file()} == before
    assert 'uncaptured sources created: 1' in capsys.readouterr().out


def test_command_with_write_writes_the_new_registers(tmp_repo):
    _old_repository(tmp_repo)
    assert migrate_registers.main(['--write']) == 0
    assert paths.PEOPLE.read_text(encoding='utf-8') == 'id,name\njane-doe,Jane Doe\n'
    assert paths.IDENTITIES.read_text(encoding='utf-8').splitlines()[0] == 'person,kind,value,source,snippet,notes'
    assert paths.AFFILIATIONS.read_text(encoding='utf-8').splitlines()[0] == (
        'id,person,organisation,from,to,status,checked,notes')
    citations = (paths.MAPPINGS_DIR / 'citations.csv').read_text(encoding='utf-8').splitlines()
    assert citations[0] == 'affiliation,source,snippet,supersedes,notes'
    assert citations[1:] == [f"{affiliation_id('jane-doe', 'acme', '2010', '')},{source_id(PAGE)},,,"]
    assert source_id(PAGE) in load_sources()
    assert read_excerpt(source_id(PAGE)).strip() == 'not captured on 2026-10-22: nothing found'
    assert not paths.AFFILIATION_PROPOSALS.exists()
    assert not paths.REJECTED_PROPOSALS.exists()
