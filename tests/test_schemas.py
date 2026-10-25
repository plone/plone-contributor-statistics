import json
from pathlib import Path
from frictionless import Schema

SCHEMAS = Path('curated/schemas')
KINDS = {'people', 'identities', 'affiliations', 'citations', 'organisations',
         'bot-accounts', 'excluded-repositories', 'events', 'talks', 'trainings', 'organisers', 'board-of-directors',
         'team-leaders', 'release-managers', 'podcasts', 'community-recognition-levels', 'community-recognition-points',
         'plips-before-github', 'sources'}
# The community files: every row cites source ids and keeps the old source cell as `cited_as` (#139)
COMMUNITY = ('events', 'talks', 'trainings', 'organisers', 'board-of-directors', 'team-leaders', 'release-managers',
             'podcasts')

def test_every_kind_has_a_valid_schema():
    assert {p.stem for p in SCHEMAS.glob('*.json')} == KINDS
    for path in SCHEMAS.glob('*.json'):
        assert Schema.from_descriptor(json.loads(path.read_text())).to_descriptor()

def test_people_and_organisations_have_opaque_ids():
    for kind in ('people', 'organisations'):
        schema = json.loads((SCHEMAS / f'{kind}.json').read_text())
        field = next(f for f in schema['fields'] if f['name'] == 'id')
        assert schema['primaryKey'] == ['id']
        assert field['constraints']['pattern'] == '^[a-z0-9][a-z0-9-]*$'

def test_set_columns_name_their_register():
    expected = {'events': {'sources': 'sources'},
                'trainings': {'trainers': 'people', 'sources': 'sources'},
                'talks': {'speakers': 'people', 'organisations': 'organisations', 'sources': 'sources'},
                'organisers': {'sources': 'sources'},
                **{kind: {'sources': 'sources'} for kind in ('board-of-directors', 'team-leaders', 'release-managers',
                                                             'podcasts')}}
    for kind, sets in expected.items():
        fields = json.loads((SCHEMAS / f'{kind}.json').read_text())['fields']
        assert {f['name']: f['x-set'] for f in fields if 'x-set' in f} == sets


def test_community_rows_cite_sources_and_keep_the_old_cell():
    for kind in COMMUNITY:
        schema = json.loads((SCHEMAS / f'{kind}.json').read_text())
        names = [f['name'] for f in schema['fields']]
        assert names[-3:] == ['sources', 'cited_as', 'notes'], kind
        fields = {f['name']: f for f in schema['fields']}
        # Only an event that holds the rows pointing to it may cite nothing itself; the check says which
        required = kind != 'events'
        assert bool(fields['sources'].get('constraints', {}).get('required')) is required, kind
        assert bool(fields['cited_as'].get('constraints', {}).get('required')) is required, kind
        assert 'source' not in fields


def test_event_kinds_and_rows_that_point_to_events():
    fields = {f['name']: f for f in json.loads((SCHEMAS / 'events.json').read_text())['fields']}
    assert fields['kind']['constraints']['enum'] == ['conference', 'symposium', 'wpd', 'sprint']
    assert fields['format']['constraints']['enum'] == ['in person', 'hybrid', 'online']
    assert fields['level']['constraints']['enum'] == ['strategic', 'community']
    assert fields['year']['type'] == 'integer'
    for kind in ('talks', 'trainings', 'organisers'):
        schema = json.loads((SCHEMAS / f'{kind}.json').read_text())
        assert {'fields': ['event'], 'reference': {'resource': 'events', 'fields': ['id']}} in schema['foreignKeys']
    organisers = json.loads((SCHEMAS / 'organisers.json').read_text())
    assert {'fields': ['person'], 'reference': {'resource': 'people', 'fields': ['id']}} in organisers['foreignKeys']
    assert {'fields': ['organisation'], 'reference': {'resource': 'organisations', 'fields': ['id']}} in (
        organisers['foreignKeys'])


def test_talk_enums():
    fields = {f['name']: f for f in json.loads((SCHEMAS / 'talks.json').read_text())['fields']}
    assert fields['type']['constraints']['enum'] == ['Keynote', 'Talk', 'Panel', 'Teaser', 'Announcement', 'Welcome',
                                                     'Recap', 'Duplicate', 'Opening', 'Full stream', 'Newsroom']
    assert fields['video']['constraints'] == {'pattern': '^https?://.*$'}
    assert [f for f in fields if fields[f].get('constraints', {}).get('required')] == [
        'id', 'event', 'type', 'title', 'sources', 'cited_as']

SOURCE_IDS = ('identities', 'citations')  # their source is a row of the source register


def test_source_requires_a_link_except_where_it_is_a_source_id():
    for path in SCHEMAS.glob('*.json'):
        schema = json.loads(path.read_text())
        fields = {f['name']: f for f in schema['fields']}
        if 'source' in fields and path.stem not in SOURCE_IDS:
            assert fields['source']['constraints']['pattern'] == '.*https?://.*'
            assert fields['source']['constraints']['required'] is True
    for kind in SOURCE_IDS:
        schema = json.loads((SCHEMAS / f'{kind}.json').read_text())
        fields = {f['name']: f for f in schema['fields']}
        assert fields['source']['constraints']['pattern'] == '^[0-9a-f]{12}$'
        assert {'fields': ['source'], 'reference': {'resource': 'sources', 'fields': ['id']}} in schema['foreignKeys']
    # Only an early commit address may have no source (the check asks for notes then)
    assert 'required' not in json.loads((SCHEMAS / 'identities.json').read_text())['fields'][3]['constraints']


def test_citations_point_to_affiliations_and_sources():
    schema = json.loads((SCHEMAS / 'citations.json').read_text())
    fields = {f['name']: f for f in schema['fields']}
    assert {'fields': ['affiliation'], 'reference': {'resource': 'affiliations', 'fields': ['id']}} in (
        schema['foreignKeys'])
    assert fields['supersedes']['x-set'] == 'sources'
    affiliations = json.loads((SCHEMAS / 'affiliations.json').read_text())
    status = next(f for f in affiliations['fields'] if f['name'] == 'status')
    assert status['constraints']['enum'] == ['stated', 'assumed', 'denied', 'proposed']


def test_an_organiser_and_a_podcast_host_may_be_empty():
    # An organiser row names a person or an organisation (the check says one of them); a podcast series may name
    # no host (#139)
    for kind, name in (('organisers', 'person'), ('organisers', 'organisation'), ('podcasts', 'person')):
        fields = {f['name']: f for f in json.loads((SCHEMAS / f'{kind}.json').read_text())['fields']}
        assert 'required' not in fields[name]['constraints']


def test_keys_make_rows_unique():
    expected = {'board-of-directors': ['year', 'person'], 'release-managers': ['year', 'person'],
                'team-leaders': ['year', 'person', 'team'], 'events': ['id'], 'talks': ['id'], 'trainings': ['id'],
                'identities': ['person', 'kind', 'value'], 'affiliations': ['id']}
    for kind, key in expected.items():
        assert json.loads((SCHEMAS / f'{kind}.json').read_text())['primaryKey'] == key
    # A source may be cited for an affiliation with several snippets; podcast hosts may be empty; an organiser row
    # has an empty person or organisation (the check keeps the rows unique)
    for kind in ('citations', 'podcasts', 'organisers'):
        assert 'primaryKey' not in json.loads((SCHEMAS / f'{kind}.json').read_text())
