import json
from pathlib import Path
from frictionless import Schema

SCHEMAS = Path('curated/schemas')
KINDS = {'people', 'identities', 'affiliations', 'citations', 'organisations',
         'bot-accounts', 'excluded-repositories', 'board-of-directors', 'team-leaders', 'release-managers', 'podcasts',
         'plone-conference-trainings', 'world-plone-day-talks', 'sprints', 'plone-conference',
         'world-plone-day-event', 'conference-talks', 'community-recognition-levels', 'community-recognition-points',
         'plips-before-github', 'sources'}

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
    expected = {'plone-conference-trainings': {'trainers': 'people'},
                'world-plone-day-talks': {'speakers': 'people', 'organisations': 'organisations'},
                'sprints': {'organisers': 'people', 'organisations': 'organisations'},
                'plone-conference': {'organisers': 'people'},
                'world-plone-day-event': {'organisers': 'people', 'organisations': 'organisations'},
                'conference-talks': {'speakers': 'people', 'organisations': 'organisations'}}
    for kind, sets in expected.items():
        fields = json.loads((SCHEMAS / f'{kind}.json').read_text())['fields']
        assert {f['name']: f['x-set'] for f in fields if 'x-set' in f} == sets


def test_conference_talk_enums():
    fields = {f['name']: f for f in json.loads((SCHEMAS / 'conference-talks.json').read_text())['fields']}
    assert fields['scope']['constraints']['enum'] == ['global', 'regional']
    assert fields['type']['constraints']['enum'] == ['Keynote', 'Talk', 'Panel']
    assert fields['video']['constraints'] == {'pattern': '^https?://.*$'}
    assert [f for f in fields if fields[f].get('constraints', {}).get('required')] == [
        'event', 'scope', 'type', 'title', 'source']

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


def test_conference_host_and_podcast_host_may_be_empty():
    # The old files have conferences and a podcast series that name no host (#139)
    for kind, name in (('plone-conference', 'organisation'), ('podcasts', 'person')):
        fields = {f['name']: f for f in json.loads((SCHEMAS / f'{kind}.json').read_text())['fields']}
        assert 'required' not in fields[name]['constraints']


def test_keys_make_rows_unique():
    expected = {'board-of-directors': ['person'], 'release-managers': ['person'], 'team-leaders': ['person', 'team'],
                'sprints': ['sprint'], 'plone-conference-trainings': ['title'], 'identities': ['kind', 'value'],
                'affiliations': ['id']}
    for kind, key in expected.items():
        assert json.loads((SCHEMAS / f'{kind}.json').read_text())['primaryKey'] == key
    # A source may be cited for an affiliation with several snippets; titles repeat; podcast hosts may be empty
    for kind in ('citations', 'world-plone-day-talks', 'podcasts'):
        assert 'primaryKey' not in json.loads((SCHEMAS / f'{kind}.json').read_text())
