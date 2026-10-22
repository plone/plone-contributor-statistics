"""The audit of the migration to citations (plan 2c): nothing of the old registers is lost in the new ones."""

import json
from dataclasses import replace
from datetime import UTC, date, datetime

from scripts.lib.model import Affiliation, Citation, Identity, Person, Source, affiliation_id
from scripts.tools.audit_migration import audit, main

PAGE = 'https://acme.example/team'
ARCHIVED = 'http://web.archive.org/web/20101010101010/https://acme.example/old'
PROFILE = 'https://github.com/janedoe'
SEARCH = 'https://github.com/search?q=author%3Ajanedoe+org%3Aacme&type=commits'
COMMIT = 'https://github.com/acme/thing/commit/abc123'
DECISION = 'https://github.com/plone/plone-contributor-statistics/pull/1#issuecomment-1'
CELL = (f'Acme team page, "Jane Doe, developer": {PAGE} ; old team page "Jane at Acme": {ARCHIVED}; '
        f'commits under acme.example {SEARCH}; she says so herself')
REJECTION = f'Reviewed: {DECISION}'


def source(sid, url, archive_url=None):
    return Source(sid, 'page', url, date(2026, 10, 22), url, archive_url, datetime(2026, 10, 22, tzinfo=UTC), None)


def old_data():
    return {
        'people': [{'id': 'jane-doe', 'name': 'Jane Doe', 'github': 'janedoe', 'source': f'Profile: {PROFILE}'},
                   {'id': 'max-muster', 'name': 'Max Muster', 'github': '', 'source': f'Team: {PAGE}'}],
        'identities': [{'person': 'jane-doe', 'kind': 'login', 'value': 'jdoe2', 'source': f'Commit: {COMMIT}'},
                       {'person': 'jane-doe', 'kind': 'email', 'value': 'jane@acme.example',
                        'source': f'Commit: {COMMIT}'}],
        'affiliations': [{'person': 'jane-doe', 'organisation': 'acme', 'from': '2010', 'to': '2014',
                          'source': CELL, 'checked': '2026-10-18', 'notes': ''},
                         {'person': 'jane-doe', 'organisation': 'acme', 'from': '2015', 'to': '',
                          'source': f'Team: {PAGE}', 'checked': '', 'notes': 'years after 2014 not verified'}],
        'rejections': [{'person': 'jane-doe', 'organisation': 'other', 'from': '2012', 'to': '2012',
                        'reason': 'a client, not her employer', 'source': REJECTION}],
        'proposals': [],
    }


def new_data():
    first = affiliation_id('jane-doe', 'acme', '2010', '2014')
    second = affiliation_id('jane-doe', 'acme', '2015', '')
    denied = affiliation_id('jane-doe', 'other', '2012', '2012')
    page_segment = f'cited as: Acme team page, "Jane Doe, developer": {PAGE}'
    old_segments = f'cited as: old team page "Jane at Acme": {ARCHIVED}'
    search_segments = f'cited as: commits under acme.example {SEARCH}; she says so herself'
    return {
        'people': [Person('jane-doe', 'Jane Doe'), Person('max-muster', 'Max Muster')],
        'identities': [
            Identity('jane-doe', 'email', 'jane@acme.example', 'c1', None, f'Commit: {COMMIT}'),
            Identity('jane-doe', 'github', 'janedoe', 'p1', None, f'Profile: {PROFILE}'),
            Identity('jane-doe', 'github-alias', 'jdoe2', 'c1', None, f'Commit: {COMMIT}'),
            Identity('max-muster', 'name', 'Max Muster', 's1', None, f'Team: {PAGE}'),
        ],
        'affiliations': [
            Affiliation(first, 'jane-doe', 'acme', 2010, 2014, 'stated', date(2026, 10, 18), None),
            Affiliation(second, 'jane-doe', 'acme', 2015, None, 'assumed', None, 'years after 2014 not verified'),
            Affiliation(denied, 'jane-doe', 'other', 2012, 2012, 'denied', None, 'a client, not her employer'),
        ],
        'citations': [
            Citation(first, 's1', 'Jane Doe, developer', None, page_segment),
            Citation(first, 's2', None, None, old_segments.replace('"Jane at Acme"', '"Jane  at Acme"')),
            Citation(first, 'c1', None, None, search_segments),
            Citation(second, 's1', None, None, f'cited as: Team: {PAGE}'),
            Citation(denied, 'd1', 'a client, not her employer', None, f'cited as: {REJECTION}'),
        ],
        'sources': {
            's1': source('s1', PAGE),
            's2': source('s2', 'https://acme.example/old', ARCHIVED.replace('http:', 'https:')),
            'p1': source('p1', PROFILE),
            'c1': source('c1', COMMIT),
            'd1': source('d1', DECISION),
        },
    }


RESULTS = [{'url': PAGE, 'source_id': 's1'}, {'url': ARCHIVED, 'source_id': 's2'},
           {'url': PROFILE, 'source_id': 'p1'}, {'url': COMMIT, 'source_id': 'c1'},
           {'url': DECISION, 'source_id': 'd1'}]
SEARCHES = {SEARCH: [COMMIT]}


def losses(old=None, new=None):
    return audit(old or old_data(), new or new_data(), RESULTS, SEARCHES).losses


def kinds(found):
    return sorted({kind for kind, _, _ in found})


def test_a_lossless_migration_has_no_losses():
    report = audit(old_data(), new_data(), RESULTS, SEARCHES)
    assert report.losses == []
    assert report.counts['affiliations'] == 2
    assert report.counts['rejections'] == 1
    assert report.counts['identities'] == 4
    assert report.counts['segments'] == 6
    assert report.counts['quotes'] == 2
    assert report.counts['labels'] == 5


def test_a_lost_segment():
    new = new_data()
    new['citations'][2] = replace(new['citations'][2], notes=f'cited as: commits under acme.example {SEARCH}')
    assert kinds(losses(new=new)) == ['segment']


def test_a_lost_quote():
    new = new_data()
    new['citations'][0] = replace(new['citations'][0], snippet=None, notes=f'cited as: {PAGE}')
    assert kinds(losses(new=new)) == ['label', 'quote', 'segment']


def test_a_label_is_read_around_its_quotes():
    # The label of `Aspeli, "Thesis", MSc dissertation: <address>` is `Aspeli, , MSc dissertation`
    cell = f'Aspeli, "Thesis", MSc dissertation: {PAGE}'
    old, new = old_data(), new_data()
    old['affiliations'][1]['source'] = cell
    new['citations'][3] = replace(new['citations'][3], notes=f'cited as: {cell}')
    assert losses(old, new) == []
    new['citations'][3] = replace(new['citations'][3], notes=f'cited as: Aspeli, "Thesis": {PAGE}')
    assert kinds(losses(old, new)) == ['label', 'segment']


def test_an_address_not_cited():
    new = new_data()
    del new['citations'][1]
    found = losses(new=new)
    assert ('cited', 'affiliation jane-doe acme 2010-2014', ARCHIVED) in found
    assert 'url' in kinds(found)


def test_a_cited_source_must_be_in_the_register():
    new = new_data()
    del new['sources']['s2']
    assert ('cited', 'affiliation jane-doe acme 2010-2014', ARCHIVED) in losses(new=new)


def test_a_search_is_cited_through_its_commits():
    new = new_data()
    new['citations'][2] = replace(new['citations'][2], source='s1')
    assert ('cited', 'affiliation jane-doe acme 2010-2014', SEARCH) in losses(new=new)


def test_changed_notes_and_reason():
    new = new_data()
    new['affiliations'][1] = replace(new['affiliations'][1], notes='changed')
    new['affiliations'][2] = replace(new['affiliations'][2], notes=None)
    assert kinds(losses(new=new)) == ['notes']
    assert len(losses(new=new)) == 2


def test_a_missing_or_changed_affiliation():
    new = new_data()
    new['affiliations'][0] = replace(new['affiliations'][0], checked=None)
    new['affiliations'][2] = replace(new['affiliations'][2], status='stated')
    assert kinds(losses(new=new)) == ['field']
    new = new_data()
    del new['affiliations'][1]
    assert ('row', 'affiliation jane-doe acme 2015-', 'no affiliation ' + affiliation_id(
        'jane-doe', 'acme', '2015', '')) in losses(new=new)


def test_identities():
    new = new_data()
    new['identities'][1] = replace(new['identities'][1], notes='')
    new['identities'][2] = replace(new['identities'][2], kind='github')
    new['identities'][3] = replace(new['identities'][3], source='p1')
    found = losses(new=new)
    assert ('notes', 'identity jane-doe github janedoe', f'Profile: {PROFILE}') in found
    assert ('row', 'identity jane-doe github-alias jdoe2', 'missing') in found
    assert ('cited', 'identity max-muster name Max Muster', 'p1') in found


def test_people():
    new = new_data()
    new['people'] = [Person('jane-doe', 'Jane D.')]
    found = losses(new=new)
    assert ('field', 'person jane-doe', 'name: Jane Doe -> Jane D.') in found
    assert ('row', 'person max-muster', 'missing') in found


def test_an_open_proposal_must_become_a_proposed_row():
    old = old_data()
    old['proposals'] = [{'person': 'jane-doe', 'organisation': 'acme', 'from': '2020', 'to': '2020',
                         'evidence': 'x'}]
    assert kinds(losses(old=old)) == ['row']


def csv_text(rows, fields):
    lines = [','.join(fields)]
    for row in rows:
        lines.append(','.join('"' + row[field].replace('"', '""') + '"' for field in fields))
    return '\n'.join(lines) + '\n'


def serve(old):
    """git_show for the old files of the fixture."""
    fields = {'people.csv': ('id', 'name', 'github', 'source'), 'identities.csv': ('person', 'kind', 'value', 'source'),
              'affiliations.csv': ('person', 'organisation', 'from', 'to', 'source', 'checked', 'notes'),
              'rejected_proposals.csv': ('person', 'organisation', 'from', 'to', 'reason', 'source'),
              'affiliation_proposals.csv': ('person', 'organisation', 'from', 'to', 'evidence')}
    key = {'people.csv': 'people', 'identities.csv': 'identities', 'affiliations.csv': 'affiliations',
           'rejected_proposals.csv': 'rejections', 'affiliation_proposals.csv': 'proposals'}
    calls = []

    def show(rev, path):
        calls.append((rev, path))
        name = path.rsplit('/', 1)[-1]
        if name == 'capture-results.jsonl':
            return '\n'.join(json.dumps(line) for line in RESULTS) + '\n'
        if name == 'searches.json':
            return json.dumps(SEARCHES)
        return csv_text(old[key[name]], fields[name])
    return show, calls


def test_main_reads_the_old_files_from_git_and_prints_the_losses(monkeypatch, capsys):
    show, calls = serve(old_data())
    monkeypatch.setattr('scripts.tools.audit_migration.git_show', show)
    monkeypatch.setattr('scripts.tools.audit_migration.read_new', new_data)
    assert main(['--rev', 'abc1234']) == 0
    assert ('abc1234', 'curated/mappings/people.csv') in calls
    assert ('abc1234', 'archive/migration-to-sources/capture-results.jsonl') in calls
    out = capsys.readouterr().out
    assert 'affiliations: 2' in out
    assert 'losses: 0' in out

    new = new_data()
    new['affiliations'][1] = replace(new['affiliations'][1], notes='changed')
    monkeypatch.setattr('scripts.tools.audit_migration.read_new', lambda: new)
    assert main(['--rev', 'abc1234']) == 1
    out = capsys.readouterr().out
    assert 'losses: 1' in out
    assert 'notes\taffiliation jane-doe acme 2015-\t' in out
