"""The community page renders from its data (design: archive/specs-and-plans/2026-10-19-community-page-design.md)."""

import json
import re
from html.parser import HTMLParser

import pytest

from scripts.report import community_page

DATA = {
    'year': 2025,
    'years': [2021, 2022, 2023, 2024, 2025],
    'headline': {'year': {'people': 151, 'organisations': 53, 'events': 9},
                 'five_years': {'people': 398, 'organisations': 89, 'events': 59},
                 'since_2003': {'people': 1046}},
    'levels': [{'name': 'Bronze Contributor', 'min': 3, 'max': 9}, {'name': 'Silver Contributor', 'min': 10, 'max': None}],
    'wall': [{'level': 'Silver Contributor', 'organisations': [{'name': 'RedTurtle', 'slug': 'redturtle', 'points': 12.0}]},
             {'level': 'Bronze Contributor', 'organisations': [
                 {'name': 'Jane Doe (independent)', 'slug': 'jane-doe-independent', 'points': 3.0}]}],
    'organisations': {
        'redturtle': {
            'name': 'RedTurtle', 'level': 'Silver Contributor', 'points': 12.0, 'next_level': None, 'points_to_next': None,
            'categories': {
                'Conference Organization': {'points': 12.0, 'contributions': [
                    {'text': 'Organized Plone Conference 2025', 'points': 12.0,
                     'file': 'curated/community-contributions/2025-plone-conference.csv', 'line': 2, 'source': None}]},
            },
            'history': {'2024': {'commits': 10, 'pull_requests': 4, 'roles': 1, 'events': 0},
                        '2025': {'commits': 20, 'pull_requests': 8, 'roles': 2, 'events': 1}},
        },
        'jane-doe-independent': {
            'name': 'Jane Doe (independent)', 'level': 'Bronze Contributor', 'points': 3.0,
            'next_level': 'Silver Contributor', 'points_to_next': 7.0,
            'categories': {
                'Team Leader': {'points': 3.0, 'contributions': [
                    {'text': 'Jane Doe (Docs Team)', 'points': 3.0,
                     'file': 'curated/community-contributions/2025-team-leaders.csv', 'line': 3,
                     'source': 'https://example.org/teams; organisation: https://github.com/janedoe; '
                               'Board: https://example.org/minutes'}]},
            },
            'history': {'2025': {'commits': 0, 'pull_requests': 0, 'roles': 1, 'events': 0}},
        },
    },
    'people': {'2025': [{'id': 'secretlogin', 'commits': 5, 'pull_requests': 2, 'roles': ['Board']},
                        {'id': 'other', 'commits': 60, 'pull_requests': 12, 'roles': []},
                        {'id': 'name:third', 'commits': 0, 'pull_requests': 0, 'roles': ['Talk']}]},
    'people_names': {'secret person': 'secretlogin'},
    'history': {
        '2005': {'people_active': 40, 'commits': 1500, 'pull_requests': None, 'board': [], 'team_leads': [],
                 'events': [{'kind': 'plone-conference', 'level': '', 'name': 'Plone Conference 2005',
                             'organisations': ['Six Feet Up'], 'sources': ['https://example.org/c2005']}]},
        '2025': {'people_active': 151, 'commits': 7502, 'pull_requests': 2107,
                 'board': [{'name': 'Anna Board', 'organisation': 'Affinitic', 'source': 'https://example.org/board'},
                           {'name': 'Bob Board', 'organisation': 'Unmapped', 'source': 'http://www.example.com"'}],
                 'team_leads': [{'name': 'Jane Doe', 'team': 'Docs Team', 'organisation': 'Jane Doe (independent)',
                                 'source': None}],
                 'events': []},
    },
}


class Assets(HTMLParser):
    """Collects the URLs of everything the page loads: scripts, styles, images, frames."""

    def __init__(self):
        super().__init__()
        self.loaded = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'img', 'iframe', 'source', 'audio', 'video') and attrs.get('src'):
            self.loaded.append(attrs['src'])
        if tag == 'link' and attrs.get('href'):
            self.loaded.append(attrs['href'])


@pytest.fixture
def page(tmp_path):
    community_page.render(DATA, tmp_path)
    return (tmp_path / 'index.html').read_text(encoding='utf-8')


def test_page_shows_the_headline_numbers(page):
    for number in ['151', '53', '9', '398', '89', '59', '1,046']:
        assert f'>{number}<' in page, number


def test_page_shows_every_organisation_on_the_wall(page):
    # Review focus: no organisation with a level is hidden
    wall = page.split('id="wall"')[1].split('</section>')[0]
    assert 'RedTurtle' in wall and 'Jane Doe (independent)' in wall
    assert 'href="#org-redturtle"' in wall


def test_contribution_without_source_links_its_row(page):
    # Review focus: no public record yet -> marked, and linked to the row on GitHub
    assert 'public record pending' in page
    assert ('https://github.com/plone/plone-contributor-statistics/blob/main/'
            'curated/community-contributions/2025-plone-conference.csv#L2') in page


def test_every_link_in_a_source_is_linked(page):
    assert 'href="https://example.org/teams"' in page
    assert 'href="https://github.com/janedoe"' in page


def test_history_without_pull_requests(page):
    # Review focus: before pull requests existed, the page says so instead of showing 0
    year_2005 = page.split('id="year-2005"')[1].split('</details>')[0]
    assert 'no pull requests yet' in year_2005
    assert '1,500' in year_2005


def test_public_roles_are_named_in_history(page):
    year_2025 = page.split('id="year-2025"')[1].split('</details>')[0]
    assert 'Anna Board' in year_2025 and 'Docs Team' in year_2025


def test_no_external_assets(page):
    assets = Assets()
    assets.feed(page)
    assert assets.loaded
    assert not [url for url in assets.loaded if re.match(r'(https?:)?//', url)]


def test_people_are_not_listed_in_the_html(page):
    # Logins appear only in the embedded data for the search, never in the visible page
    data = page.split('<script type="application/json" id="people-data">')[1].split('</script>')[0]
    assert json.loads(data)['years']['2025'][0]['id'] == 'secretlogin'
    assert json.loads(data)['names'] == {'secret person': 'secretlogin'}
    assert page.count('secretlogin') == 2  # both inside the data element


def test_links_to_the_docs(page):
    assert 'href="docs/"' in page
    assert 'href="docs/explanation/community-page.html' in page


def test_static_files_are_copied(tmp_path):
    community_page.render(DATA, tmp_path)
    assert (tmp_path / 'static' / 'site.css').exists()
    assert (tmp_path / 'static' / 'site.js').exists()


def test_renders_the_committed_data(tmp_path):
    community_page.render(json.loads(community_page.paths.COMMUNITY_PAGE.read_text(encoding='utf-8')), tmp_path)
    page = (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert 'kitconcept GmbH' in page


def test_links_to_the_same_site_are_numbered(page):
    assert '>example.org</a>' in page and '>example.org (2)</a>' in page


def test_unmapped_is_not_shown_as_an_organisation(page):
    year_2025 = page.split('id="year-2025"')[1].split('</details>')[0]
    assert 'Bob Board' in year_2025 and 'Unmapped' not in year_2025


def test_quotes_are_not_part_of_links(page):
    assert 'href="http://www.example.com"' in page
    assert 'example.com&#34;' not in page and 'example.com"<' not in page


def test_people_show_anonymous_distributions(page):
    # Without a search, the People tab shows how many people did how much, without names
    people = page.split('id="people"')[1].split('</section>')[0]
    distribution = people.split('class="distribution"')[1].split('</table>')[0]
    assert '2025' in distribution
    assert 'secretlogin' not in distribution and 'other' not in distribution
    # merged pull requests: 1 person with 2-9, 1 person with 10-49; commits: 1 with 2-9, 1 with 50+
    assert re.search(r'Merged pull requests.*?<td>0</td><td>1</td><td>1</td><td>0</td>', distribution, re.S)
    assert re.search(r'Commits.*?<td>0</td><td>1</td><td>0</td><td>1</td>', distribution, re.S)


def test_page_says_all_data_comes_from_public_records(page):
    # Prominent, right after the headline numbers, with the rule and its one exception linked
    first_screen = page.split('id="wall"')[0]
    statement = first_screen.split('id="public-records"')[1]
    assert 'public records' in statement
    assert 'href="docs/index.html#public-records-only"' in statement
    assert 'href="docs/how-to/link-old-commits-to-a-person.html"' in statement
