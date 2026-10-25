"""The work list of the sources the community files cite: offline, with files in a temporary repository."""

import json

import pytest

from scripts.lib import paths
from scripts.tools import community_sources
from scripts.tools.community_sources import work_list

VIDEO = 'https://www.youtube.com/watch?v=abcdefghijk'
PLAYLIST = 'https://www.youtube.com/playlist?list=PLabc'
SPRINT = 'https://plone.org/events/sprint-report'
MINUTES = 'https://plone.org/foundation/minutes'


def write(path, header, rows):
    path.write_text(header + '\n' + ''.join(row + '\n' for row in rows), encoding='utf-8')


@pytest.fixture
def repo(tmp_repo):
    write(paths.PEOPLE, 'id,name', ['jane-doe,Jane Doe', 'john-roe,John Roe', 'ann-lee,Ann Lee'])
    write(paths.IDENTITIES, 'person,kind,value,source,snippet,notes', [
        'jane-doe,name,Jane M. Doe,https://a.org/n,,', 'jane-doe,login,jdoe,https://a.org/n,,'])
    write(paths.ORGANISATIONS, 'id,name,kind,github,aliases,notes', [
        'acme,Acme,organisation,,Acme GmbH;ACME Inc.,', 'beta,Beta,organisation,,,'])
    community = paths.COMMUNITY
    write(community / '2021-world-plone-day-talks.csv', 'title,speakers,organisations,type,location,source,notes', [
        f'A talk,jane-doe;john-roe,acme,Talk,Online,"Recording: {VIDEO}",'])
    write(community / '2014-sprints.csv', 'sprint,start,end,location,organisers,organisations,level,source,notes', [
        f'Sprint,2014-01-01,2014-01-05,Here,ann-lee,beta,community,'
        f'"report: {SPRINT}; Board minutes: {MINUTES}; Recordings: {PLAYLIST}",'])
    write(community / '2017-conference-talks.csv', 'event,scope,type,title,speakers,organisations,video,source,notes', [
        f'Conf,all,Talk,Another,ann-lee,,https://vimeo.com/123,'
        f'"""Ann Lee leads Beta."", Plone Conference 2017 speaker page: https://2017.ploneconf.org/ann",'])
    write(community / '2020-release-managers.csv', 'person,source,notes', [
        f'jane-doe,https://github.com/plone/release,'])
    return tmp_repo


def by_url(items):
    return {item['url']: item for item in items}


def test_every_url_of_a_cell_is_an_item(repo):
    found = by_url(work_list())
    assert [item['url'] for item in work_list()] == sorted(found)
    for url in (SPRINT, MINUTES, PLAYLIST):
        assert found[url]['names'] == ['Ann Lee', 'Beta']
    assert found[SPRINT]['kind'] is None


def test_video_source_gets_the_speakers(repo):
    item = by_url(work_list())[VIDEO]
    assert item == {'url': VIDEO, 'quotes': [], 'kind': 'video',
                    'names': ['Jane Doe', 'Jane M. Doe', 'John Roe', 'Acme', 'Acme GmbH', 'ACME Inc.']}
    assert by_url(work_list())[PLAYLIST]['kind'] == 'video'  # refused by the capture, still an item


def test_names_from_people_and_organisations(repo):
    page = by_url(work_list())['https://2017.ploneconf.org/ann']
    assert page == {'url': 'https://2017.ploneconf.org/ann', 'quotes': ['Ann Lee leads Beta.'],
                    'names': ['Ann Lee'], 'kind': 'speaker-page'}
    assert by_url(work_list())['https://github.com/plone/release']['names'] == ['Jane Doe', 'Jane M. Doe']


def test_video_column_is_not_a_source(repo):
    assert 'https://vimeo.com/123' not in by_url(work_list())


def test_split_by_videos(repo, tmp_path, capsys):
    out = tmp_path / 'list.jsonl'
    assert community_sources.main(['--worklist', str(out), '--videos-only']) == 0
    lines = [json.loads(line) for line in out.read_text(encoding='utf-8').splitlines()]
    assert [line['url'] for line in lines] == [PLAYLIST, VIDEO]
    assert '2 items, 2 videos, 0 already registered' in capsys.readouterr().out
    assert community_sources.main(['--worklist', str(out), '--no-videos']) == 0
    lines = [json.loads(line) for line in out.read_text(encoding='utf-8').splitlines()]
    assert all(line['kind'] != 'video' for line in lines) and len(lines) == 4


def test_registered_urls_are_counted(repo, tmp_path, capsys):
    from tests.conftest import record_source
    record_source(SPRINT)
    assert community_sources.main(['--worklist', str(tmp_path / 'l.jsonl')]) == 0
    assert '1 already registered' in capsys.readouterr().out


def test_names_of_world_plone_day_organisers_and_the_conference_organisation(repo):
    community = paths.COMMUNITY
    write(community / '2025-world-plone-day-event.csv', 'date,location,format,organisations,organisers,source,notes', [
        '2025-04-10,"Bologna, Italy",in person,acme,john-roe,https://wpd.example.org/bologna,'])
    write(community / '2025-plone-conference.csv', 'organisation,organisers,source,notes', [
        'beta,ann-lee,https://conf.example.org/2025,'])
    found = by_url(work_list())
    assert found['https://wpd.example.org/bologna']['names'] == ['John Roe', 'Acme', 'Acme GmbH', 'ACME Inc.']
    assert found['https://conf.example.org/2025']['names'] == ['Ann Lee', 'Beta']


def test_the_video_hosts_are_those_of_the_model():
    from scripts.lib.model import community
    assert community_sources.VIDEO_HOSTS is community.VIDEO_HOSTS
    assert community_sources.is_video('https://www.plone.tv/a-talk') and not community_sources.is_video(SPRINT)
