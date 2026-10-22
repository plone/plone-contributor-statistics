"""Reading the commit domains per person and year."""
from collections import Counter

import pytest

from scripts.lib import paths
from scripts.lib.commit_domains import load_commit_domains, organisation_commits
from scripts.lib.model import load_registry


def write_year(year, rows):
    paths.commit_domains_file(year).write_text(
        'username,domain,commits\n' + ''.join(f'{u},{d},{n}\n' for u, d, n in rows), encoding='utf-8')


def test_load_commit_domains(tmp_repo):
    write_year(2020, [('jane', 'acme.example', 3), ('jane', 'gmail.com', 1), ('person:bo', 'other.example', 2)])
    assert load_commit_domains(2020) == {
        'jane': Counter({'acme.example': 3, 'gmail.com': 1}),
        'person:bo': Counter({'other.example': 2}),
    }


def test_header_only_year_is_empty(tmp_repo):
    write_year(2021, [])
    assert load_commit_domains(2021) == {}


def test_missing_year_raises(tmp_repo):
    with pytest.raises(FileNotFoundError):
        load_commit_domains(1999)


def test_organisation_commits_splits_personal_and_unmatched(tmp_repo, write_registers):
    write_registers(organisations=[('acme', 'Acme')])
    counts = Counter({'acme.example': 5, 'mail.acme.example': 2, 'gmail.com': 3, 'nobody.example': 4})
    per_organisation, personal, unmatched = organisation_commits(counts, load_registry())
    assert per_organisation == Counter({'acme': 7})
    assert personal == 3
    assert unmatched == 4
