"""Community roles and events, read in one place (community page)."""

import pytest

from scripts.lib import community


def write(folder, name, text):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text, encoding='utf-8')


@pytest.fixture
def folder(tmp_path):
    return tmp_path / 'community'


def test_trainers_are_split_and_paired_with_handles_and_organisations(folder):
    write(folder, '2025-plone-conference-trainings.csv', 'Title,Trainer(s),GitHub Handle(s),Organisation,Source\n'
          'Volto,Timo;Mauro,tisto;mamico,kitconcept GmbH;RedTurtle,https://example.org/t\n')
    records = community.community_records(2025, folder)
    assert [(r.person, r.handle, r.organisation, r.label, r.detail) for r in records] == [
        ('Timo', 'tisto', 'kitconcept GmbH', 'Trainer', 'Volto'),
        ('Mauro', 'mamico', 'RedTurtle', 'Trainer', 'Volto'),
    ]


def test_only_talks_count_as_wpd_roles(folder):
    write(folder, '2025-world-plone-day-talks.csv', 'Video Title,Speaker(s),Organisation,Event / Location,Type,YouTube ID\n'
          'A talk,Mauro,RedTurtle,Online,Talk,abc\nA teaser,Mauro,RedTurtle,Online,Teaser,def\n')
    [talk] = community.community_records(2025, folder)
    assert (talk.label, talk.detail, talk.source) == ('Talk', 'A talk', 'https://www.youtube.com/watch?v=abc')


def test_records_carry_file_line_and_source(folder):
    write(folder, '2025-team-leaders.csv', 'Name,Team,Organisation,Source\n'
          'Timo,Volto Team,kitconcept GmbH,https://a\nMauro,Classic UI Team,RedTurtle,https://b\n')
    second = community.community_records(2025, folder)[1]
    assert (second.kind, second.year, second.line, second.source, second.detail) == (
        'team-leaders', 2025, 3, 'https://b', 'Classic UI Team')
    assert second.file.endswith('2025-team-leaders.csv')


def test_world_plone_day_is_one_event_per_local_event_held_in_person(folder):
    write(folder, '2025-world-plone-day-event.csv', 'Date,Location,Format,Organisation,Source,Notes\n'
          '2025-04-10,Bologna,in person,RedTurtle,https://bologna,\n'
          '2025-04-10,Brasília,in person,PloneGov-BR;Simples Consultoria,https://brasilia,\n'
          '2025-04-10,Online,online,kitconcept GmbH,https://online,\n')
    bologna, brasilia = community.events(2025, folder)
    assert bologna.name == 'World Plone Day 2025, Bologna'
    assert brasilia.organisations == ('PloneGov-BR', 'Simples Consultoria')
    assert brasilia.sources == ('https://brasilia',)


def test_every_recorded_sprint_is_an_event(folder):
    # Strategic, community and sprints without a level alike
    write(folder, '2020-sprints.csv', 'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
          'Sprint A,,,Ferrara,Jane;John,RedTurtle;Syslab,strategic,https://a,\n'
          'Sprint B,,,Bonn,Joe,Codesyntax,community,https://b,\n'
          'Sprint C,,,Online,Ann,Unmapped,,https://c,\n')
    events = community.events(2020, folder)
    assert [(e.kind, e.name, e.organisations, e.level) for e in events] == [
        ('sprints', 'Sprint A', ('RedTurtle', 'Syslab'), 'strategic'),
        ('sprints', 'Sprint B', ('Codesyntax',), 'community'),
        ('sprints', 'Sprint C', ('Unmapped',), ''),
    ]


def test_sprint_organisers_are_roles(folder):
    write(folder, '2020-sprints.csv', 'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\nSprint A,,,Ferrara,Jane;John,RedTurtle;Syslab,strategic,https://a,\n')
    records = community.community_records(2020, folder)
    assert [(r.person, r.organisation, r.label, r.detail) for r in records] == [
        ('Jane', 'RedTurtle', 'Sprint organiser', 'Sprint A'), ('John', 'Syslab', 'Sprint organiser', 'Sprint A')]


def test_conference_is_one_event_per_year(folder):
    write(folder, '2024-plone-conference.csv', 'Organisation\nPloneGov-BR\nInterlegis Program (Senado Federal)\n')
    [event] = community.events(2024, folder)
    assert (event.kind, event.name, len(event.organisations)) == ('plone-conference', 'Plone Conference 2024', 2)


def test_missing_kinds_are_no_events(folder):
    folder.mkdir()
    assert community.events(2025, folder) == []


def test_records_of_rows_with_several_people_are_shared(folder):
    write(folder, '2020-sprints.csv', 'Sprint,Start,End,Location,Organiser(s),Organisation,Level,Source,Notes\n'
          'Sprint A,,,X,Jane;John,RedTurtle,strategic,https://a,\nSprint B,,,X,Joe,Syslab,community,https://b,\n')
    assert [(r.person, r.shared) for r in community.community_records(2020, folder)] == [
        ('Jane', True), ('John', True), ('Joe', False)]
