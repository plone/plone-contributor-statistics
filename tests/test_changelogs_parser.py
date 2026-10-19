"""Parsing changelog files: release headers, entries, names and dates (#71)."""

import pytest

from scripts.lib import changelogs
from scripts.lib.changelogs import extract_names, parse_changelog, parse_date


@pytest.mark.parametrize('header, date', [
    ('1.2.3 (2010-05-04)', '2010-05-04'),
    ('1.2.3 - 2010-05-04', '2010-05-04'),
    ('Plone 2.0.5 - Backed Up Willie - Released December 1, 2004', '2004-12-01'),
    ('Plone 3.0.6 - released Febuary 15, 2008', '2008-02-15'),
    ('RC1 - Released September 12, 2006', '2006-09-12'),
    ('6.1.0 (2025-01-01)', '2025-01-01'),
    ('1.0 - 12.03.2008', '2008-03-12'),
    ('2.1 - 1 March 2009', '2009-03-01'),
    ('1.1 (2008-xx-xx)', '2008'),
    ('2.0 - March 2004', '2004-03'),
    ('1.0 (unreleased)', ''),
    ('Changelog', ''),
])
def test_parse_date(header, date):
    assert parse_date(header) == date


RST = """\
Changelog
=========

1.1 (unreleased)
----------------

- Nothing changed yet.


1.0.1 (2010-05-04)
------------------

Bug fixes:

- Fixed the portlet.
  [hannosch]

- Fixed a long line that goes on
  on a second line, with a sub list:

  - a detail

  [alecm, timo]

1.0 (2009-12-01)
----------------

* Initial release [hannosch]
"""


def test_rst_sections_and_entries():
    entries = parse_changelog(RST)

    assert [(e.release_date, e.text.split('\n')[0]) for e in entries] == [
        ('', 'Nothing changed yet.'),
        ('2010-05-04', 'Fixed the portlet.'),
        ('2010-05-04', 'Fixed a long line that goes on'),
        ('2009-12-01', 'Initial release [hannosch]'),
    ]
    assert entries[0].unreleased
    # A category heading such as "Bug fixes:" keeps the release; continuation lines and sub-bullets belong to the entry
    assert entries[2].text == 'Fixed a long line that goes on\non a second line, with a sub list:\n- a detail\n[alecm, timo]'
    assert entries[1].version == '1.0.1'
    assert entries[1].line == 15


def test_markdown_headers():
    entries = parse_changelog('# Changelog\n\n## 6.1.0 (2025-01-01)\n\n### Bug fixes\n\n- Fix it. @davisagli #123\n')

    assert [(e.version, e.release_date, e.text) for e in entries] == [('6.1.0', '2025-01-01', 'Fix it. @davisagli #123')]


def test_old_flush_left_headers():
    text = ("Plone 2.0.5 - Backed Up Willie - Released December 1, 2004\n\n"
            "    - Fixed the login form [limi]\n\n"
            "RC1 - Released September 12, 2006\n\n"
            "    * Added the calendar [tiran]\n")

    entries = parse_changelog(text)

    assert [(e.release_date, e.text) for e in entries] == [
        ('2004-12-01', 'Fixed the login form [limi]'), ('2006-09-12', 'Added the calendar [tiran]')]


def test_entries_before_the_first_header_are_not_entries():
    assert parse_changelog('Some intro text\n\n- a list item [limi]\n') == []


@pytest.mark.parametrize('text, names, variant', [
    ('Fixed the portlet. [hannosch]', ['hannosch'], 'bracket_end'),
    ('Fixed the portlet [a, b]', ['a', 'b'], 'bracket_end'),
    ('Fixed the portlet [a and b]', ['a', 'b'], 'bracket_end'),
    ('Fixed the portlet [a] [b]', ['a', 'b'], 'bracket_end'),
    ('Fixed the portlet [a/b]', ['a', 'b'], 'bracket_end'),
    ('Fixed the portlet [applied by kleist]', ['kleist'], 'bracket_end'),
    ('Fixed the portlet [Eric Brehault]', ['Eric Brehault'], 'bracket_end'),
    ('Fixed the portlet [hannosch] (#123)', ['hannosch'], 'bracket_end'),
    ('Fixed the portlet [hannosch]\nhttps://dev.plone.org/ticket/123', ['hannosch'], 'bracket_end'),
    ('Fixed the portlet\n[hannosch]\nSee the upgrade notes.', ['hannosch'], 'bracket_line'),
    ('Fix the portlet. @davisagli', ['davisagli'], 'at'),
    ('Fix the portlet. @davisagli, @stevepiercy #123', ['davisagli', 'stevepiercy'], 'at'),
    ('Fixed the portlet -- Alec Mitchell', ['Alec Mitchell'], 'dash'),
    ('Fixed the portlet (hopefully)', ['hopefully'], 'paren'),
    ('Fixed the portlet (optional)', [], 'none'),
    ('Fixed the portlet [plone devs]', [], 'bracket_end'),
    ('Fixed the portlet in [1]', [], 'none'),
    ('Fixed the portlet', [], 'none'),
])
def test_extract_names(text, names, variant):
    assert extract_names(text) == (names, variant)


def test_strip_refs():
    assert changelogs.strip_refs('Fix it [a] (#12, #13)') == 'Fix it [a]'
    assert changelogs.strip_refs('Fix it [a] https://github.com/plone/x/issues/1') == 'Fix it [a]'
    assert changelogs.strip_refs('Fix it [a] Fixes #1.') == 'Fix it [a]'


@pytest.mark.parametrize('path, counted', [
    ('CHANGES.rst', True),
    ('docs/HISTORY.txt', True),
    ('Products/CMFPlone/HISTORY.txt', True),
    ('CHANGELOG.md', True),
    ('news/123.bugfix', False),
    ('README.rst', False),
    ('src/plone/tests/CHANGES.rst', False),
    ('templates/{{cookiecutter.name}}/CHANGES.rst', False),
    ('skins/jscalendar/ChangeLog', False),
    ('node_modules/x/CHANGELOG.md', False),
])
def test_changelog_files(path, counted):
    assert changelogs.is_changelog_file('plone.app.x', path) is counted


def test_aggregated_release_notes_are_skipped():
    assert not changelogs.is_changelog_file('buildout.coredev', 'release/changelog.txt')
    assert changelogs.is_changelog_file('other', 'release/changelog.txt')


def test_gnu_changelogs_are_recognized():
    gnu = ('2005-07-22 Hanno Schlichting <plone@hannosch.info>\n\n    * Correct failing test\n\n'
           '2004-07-24  Christian Heimes <heimes@faho.rwth-aachen.de>\n\n    * Changed version\n')

    assert changelogs.is_gnu_changelog(gnu)
    assert not changelogs.is_gnu_changelog(RST)


def test_text_hash_ignores_emphasis_case_and_whitespace():
    assert changelogs.text_hash('Fixed *the*  ``portlet`` [a]') == changelogs.text_hash('fixed the\nportlet [a]')
    assert changelogs.text_hash('Release on PyPI [a]') != changelogs.text_hash('Release on PyPI [b]')
