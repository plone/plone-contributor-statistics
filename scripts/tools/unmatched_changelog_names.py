#!/usr/bin/env python3
"""List changelog names that no mapping file maps, and propose who they are (#71).

Reads the changelog files from the clones in the cache, as
`make run-changelogs` left them, and lists the names without a mapping, by
their number of entries. With --propose, it looks for the commits whose
message repeats an entry with that name, in the same repository. When most
of these commits have the same author, it prints a row for
curated/mappings/changelog_names.csv: the changelog entry and the commit are
its public records. Commits of patches that someone else applied name the
committer instead of the author, so a person checks each row before adding
it; see docs/how-to/link-old-commits-to-a-person.md.
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict

import requests
from dotenv import load_dotenv

from scripts.collect import plone_changelogs
from scripts.lib import changelogs, git_history, paths
from scripts.lib.github_api import github_graphql
from scripts.lib.mappings import load_account_aliases, load_excluded_repositories

def load_commit_author_rows():
    """(email, login or None, name) of the rows of commit_authors.csv."""
    with open(paths.COMMIT_AUTHORS, newline='', encoding='utf-8') as f:
        return [(row['email'].strip().lower(), row['github_username'].strip() or None, row['name'].strip())
                for row in csv.DictReader(f)]


# Entries shorter than this are too generic to find their commit
MIN_TEXT = 25


def message_key(text):
    """The text of an entry or a commit message to compare: without names and references, letters and digits only."""
    text = changelogs.strip_refs(text)
    text = re.sub(r'(\s*\[[^\[\]]+\])+\s*\.?\s*$', '', text)
    text = re.sub(r'[^a-z0-9 ]', ' ', changelogs.normalise(text))
    return ' '.join(text.split())


def unmatched_entries(entries, mapper, years):
    """{name: [entries]} of the entries in the years with a name that no mapping file maps."""
    found = defaultdict(list)
    spelling = {}
    for entry in entries:
        if not entry.year or int(entry.year) not in years:
            continue
        for person, name, layer in changelogs.credited(entry, mapper):
            if layer == changelogs.UNMATCHED:
                key = spelling.setdefault(person.casefold(), person)
                found[key].append(entry)
    return dict(found)


def find_commits(entries, commits):
    """{entry: the first commit whose message repeats the entry}, for the entries of one repository."""
    index = defaultdict(list)
    keyed = [(message_key(commit['message']), commit) for commit in commits]
    for key, commit in keyed:
        index[key[:MIN_TEXT]].append((key, commit))
    found = {}
    for entry in entries:
        key = message_key(entry.text)[:60]
        if len(key) < MIN_TEXT:
            continue
        hits = [commit for message, commit in index.get(key[:MIN_TEXT], []) if message.startswith(key[:50])]
        if not hits and len(key) >= 40:
            hits = [commit for message, commit in keyed if key in message]
        if hits:
            # The first commit, not later cherry-picks
            found[id(entry)] = min(hits, key=lambda commit: commit['date'])
    return found


def evidence(unmatched, commits_of):
    """{name: {'authors': Counter((email, author name)), 'examples': {email: (entry, commit)}}}.

    Only entries with one name are evidence: an entry of two people has one author.
    `commits_of(repository)` returns the commit messages of a repository.
    """
    by_repository = defaultdict(list)
    for name, entries in unmatched.items():
        for entry in entries:
            if len(entry.names) == 1:
                by_repository[entry.repository].append((name, entry))
    found = defaultdict(lambda: {'authors': Counter(), 'examples': {}})
    for repository, items in sorted(by_repository.items()):
        commits = find_commits([entry for _, entry in items], commits_of(repository))
        for name, entry in items:
            commit = commits.get(id(entry))
            if commit:
                author = (commit['author_email'].lower(), commit['author_name'])
                found[name]['authors'][author] += 1
                found[name]['examples'].setdefault(author[0], (entry, commit))
    return dict(found)


def proposals(unmatched, found, resolve, min_share=0.8):
    """Rows for changelog_names.csv: (changelog_name, github_username, name, source, entries, commits, share).

    `resolve(email, entry, commit)` returns (GitHub login, name) of the commit author; the login is
    None for a person without a GitHub account, and the name None if only the commit knows it.
    """
    rows = []
    for name, data in sorted(found.items(), key=lambda item: item[0].casefold()):
        total = sum(data['authors'].values())
        (email, author), commits = data['authors'].most_common(1)[0]
        share = commits / total
        if share < min_share:
            continue
        entry, commit = data['examples'][email]
        login, person = resolve(email, entry, commit)
        commit_url = f"https://github.com/plone/{entry.repository}/commit/{commit['sha']}"
        source = f'Changelog entry: {entry.url}; the commit by {author} that repeats it: {commit_url}'
        rows.append((name, login or '', '' if login else person or author, source, len(unmatched[name]), commits,
                     round(share, 2)))
    return rows


class Resolver:
    """The commit author: commit_authors.csv, else the account GitHub links to the commit."""

    def __init__(self, session):
        self.session = session
        self.commit_authors = {email: (login, name) for email, login, name in load_commit_author_rows()}
        self.aliases = load_account_aliases()

    def __call__(self, email, entry, commit):
        login, name = self.commit_authors.get(email, (None, None))
        if name and not login:
            return None, name
        if not login:
            query = ('query($owner: String!, $name: String!, $oid: GitObjectID!) { repository(owner: $owner, '
                     'name: $name) { object(oid: $oid) { ... on Commit { author { user { login } } } } } }')
            data = github_graphql(self.session, query, {'owner': plone_changelogs.ORGANISATION,
                                                        'name': entry.repository, 'oid': commit['sha']})
            user = (((data.get('repository') or {}).get('object') or {}).get('author') or {}).get('user')
            login = user['login'] if user else None
        return self.aliases.get(login, login), name


def main():
    parser = argparse.ArgumentParser(description='List changelog names without a mapping (#71)')
    parser.add_argument('--from-year', type=int, default=changelogs.REPORTED_YEARS[0],
                        help=f'First year (default: {changelogs.REPORTED_YEARS[0]})')
    parser.add_argument('--to-year', type=int, default=changelogs.REPORTED_YEARS[-1],
                        help=f'Last year (default: {changelogs.REPORTED_YEARS[-1]})')
    parser.add_argument('--propose', action='store_true',
                        help='Propose people from the commits that repeat the entries (needs GITHUB_TOKEN)')
    parser.add_argument('--min-share', type=float, default=0.8,
                        help="Share of the matching commits the author must have (default: 0.8)")
    args = parser.parse_args()
    years = range(args.from_year, args.to_year + 1)

    excluded = load_excluded_repositories()
    repositories = [repo for repo in plone_changelogs.cached_repositories() if repo[0] not in excluded]
    occurrences = plone_changelogs.collect(repositories, update=False, log=lambda line: None)
    unmatched = unmatched_entries(changelogs.deduplicate(occurrences), plone_changelogs.name_mapper(), years)
    for name, entries in sorted(unmatched.items(), key=lambda item: (-len(item[1]), item[0].casefold())):
        found_years = sorted(entry.year for entry in entries)
        print(f'{name}\t{len(entries)} entries\t{found_years[0]}–{found_years[-1]}')
    print(f'{len(unmatched)} changelog names without a mapping in {years[0]}–{years[-1]}', file=sys.stderr)

    if args.propose:
        load_dotenv()
        session = requests.Session()
        token = os.getenv('GITHUB_TOKEN')
        if token:
            session.headers['Authorization'] = f'token {token}'
        default_branches = dict(repositories)

        def commits_of(repository):
            path = os.path.join(git_history.CACHE_DIR, plone_changelogs.ORGANISATION, f'{repository}.git')
            default = default_branches[repository]
            branches = [default] + git_history.release_branches(git_history.list_branches(path), default)
            return git_history.commit_messages(path, branches)

        rows = proposals(unmatched, evidence(unmatched, commits_of), Resolver(session), args.min_share)
        print('\nProposals (check each before adding; the last three columns are not part of the file):')
        writer = csv.writer(sys.stdout, lineterminator='\n')
        writer.writerow(['changelog_name', 'github_username', 'name', 'source', 'entries', 'commits', 'share'])
        writer.writerows(rows)


if __name__ == '__main__':
    main()
