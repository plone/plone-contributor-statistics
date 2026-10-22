"""Read the mail domains of the commit authors per person and year.

Collected by `scripts.collect.plone_commit_domains`.
"""
import csv
from collections import Counter, defaultdict

from scripts.lib import paths
from scripts.lib.commit_authors import is_company_domain


def load_commit_domains(year):
    """{username: Counter({domain: commits})} of a year; {} when no commit was identified.

    Raises FileNotFoundError when the year was never collected.
    """
    counts = defaultdict(Counter)
    with open(paths.commit_domains_file(year), newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            counts[row['username']][row['domain']] += int(row['commits'])
    return dict(counts)


def organisation_commits(counts, registry):
    """(commits per organisation id, commits under personal domains, commits under unmatched company domains).

    `counts` is the Counter of one person, as `load_commit_domains` returns it.
    """
    per_organisation, personal, unmatched = Counter(), 0, 0
    for domain, commits in counts.items():
        if not is_company_domain(domain):
            personal += commits
        elif (match := registry.match_domain(domain)) is None:
            unmatched += commits
        else:
            per_organisation[match[0]] += commits
    return per_organisation, personal, unmatched
