import json
from pathlib import Path
from frictionless import Schema

SCHEMAS = Path('curated/schemas')
KINDS = {'people', 'identities', 'affiliations', 'organisations', 'affiliation-proposals', 'rejected-proposals',
         'bot-accounts', 'excluded-repositories', 'board-of-directors', 'team-leaders', 'release-managers', 'podcasts',
         'plone-conference-trainings', 'world-plone-day-talks', 'sprints', 'plone-conference',
         'world-plone-day-event', 'conference-talks', 'community-recognition-levels', 'community-recognition-points',
         'plips-before-github'}

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

def test_source_requires_a_link_except_for_identities():
    for path in SCHEMAS.glob('*.json'):
        fields = {f['name']: f for f in json.loads(path.read_text())['fields']}
        if 'source' in fields and path.stem != 'identities':
            assert fields['source']['constraints']['pattern'] == '.*https?://.*'
            assert fields['source']['constraints']['required'] is True


def test_conference_host_and_podcast_host_may_be_empty():
    # The old files have conferences and a podcast series that name no host (#139)
    for kind, name in (('plone-conference', 'organisation'), ('podcasts', 'person')):
        fields = {f['name']: f for f in json.loads((SCHEMAS / f'{kind}.json').read_text())['fields']}
        assert 'required' not in fields[name]['constraints']


def test_keys_make_rows_unique():
    expected = {'board-of-directors': ['person'], 'release-managers': ['person'], 'team-leaders': ['person', 'team'],
                'sprints': ['sprint'], 'plone-conference-trainings': ['title'], 'identities': ['kind', 'value']}
    for kind, key in expected.items():
        assert json.loads((SCHEMAS / f'{kind}.json').read_text())['primaryKey'] == key
    # A person has several rows (the overlap check covers affiliations); titles repeat; podcast hosts may be empty
    for kind in ('affiliations', 'world-plone-day-talks', 'podcasts'):
        assert 'primaryKey' not in json.loads((SCHEMAS / f'{kind}.json').read_text())
