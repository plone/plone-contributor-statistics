#!/usr/bin/env python3
"""List changelog names that the registers do not map, and propose who they are (#71).

Reads the changelog files from the clones in the cache, as
`make run-changelogs` left them, and lists the names without a mapping, by
their number of entries. With --propose, it looks for the commits whose
message repeats an entry with that name, in the same repository. When most
of these commits have the same author, it prints the command that captures
the commit as a source, and a row for curated/mappings/identities.csv that
cites it, with the author line as the snippet and the changelog entry and
the commit in the notes. It writes nothing itself: run the capture command,
then add the row. Commits of patches that someone else applied name the
committer instead of the author, so a person checks each row before adding
it; see docs/how-to/link-old-commits-to-a-person.md.
"""

import argparse
import csv
import os
import re
import shlex
import sys
from collections import Counter, defaultdict

import requests
from dotenv import load_dotenv

from scripts.collect import plone_changelogs
from scripts.lib import changelogs, git_history
from scripts.lib.github_api import github_graphql
from scripts.lib.model import load_excluded_repositories, load_registry, source_id

# Entries shorter than this are too generic to find their commit
MIN_TEXT = 25
# The columns --propose prints: those of identities.csv, then three that are not part of the file
HEADER = ['person', 'kind', 'value', 'source', 'snippet', 'notes', 'entries', 'commits', 'share']


def message_key(text):
    """The text of an entry or a commit message to compare: without names and references, letters and digits only."""
    text = changelogs.strip_refs(text)
    text = re.sub(r'(\s*\[[^\[\]]+\])+\s*\.?\s*$', '', text)
    text = re.sub(r'[^a-z0-9 ]', ' ', changelogs.normalise(text))
    return ' '.join(text.split())


def unmatched_entries(entries, mapper, years):
    """{name: [entries]} of the entries in the years with a name that the registers do not map."""
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


def capture_command(commit_url, email):
    """The shell command that captures the commit as a source, finding its author by the address."""
    return f'python -m scripts.tools.capture {shlex.quote(commit_url)} --name {shlex.quote(email)}'


def proposals(unmatched, found, resolve, registry, min_share=0.8):
    """[(capture command, row)]: the command that captures the commit, and the row for identities.csv citing it,
    (person, 'name', changelog name, source, snippet, notes, entries, commits, share).

    `resolve(email, entry, commit)` returns the GitHub login of the commit author, None for a person
    without a GitHub account. The person is the one the register has for the login, else for the email
    address; when it has none, the person cell is a note and the row is not meant to be added as it is.
    The source is the id the commit gets once captured, the snippet its author line as the capture stores it.
    The last three columns are not part of the file. Nothing is written.
    """
    rows = []
    for name, data in sorted(found.items(), key=lambda item: item[0].casefold()):
        total = sum(data['authors'].values())
        (email, author), commits = data['authors'].most_common(1)[0]
        share = commits / total
        if share < min_share:
            continue
        entry, commit = data['examples'][email]
        login = resolve(email, entry, commit)
        person = (registry.person_for(login=login) if login else None) or registry.person_for(email=email)
        if person:
            who = person.id
        elif login:
            who = f'?no person for the login {login}'
        else:
            who = f'?no person for {author} <{email}>'
        commit_url = f"https://github.com/plone/{entry.repository}/commit/{commit['sha']}"
        notes = f'Changelog entry: {entry.url}; the commit by {author} that repeats it: {commit_url}'
        snippet = f"Author: {commit['author_name']} <{commit['author_email']}>"
        rows.append((capture_command(commit_url, commit['author_email']),
                     (who, 'name', name, source_id(commit_url), snippet, notes, len(unmatched[name]), commits,
                      round(share, 2))))
    return rows


def print_proposals(found):
    """Print the header, then for each proposal its capture command as a comment and its row."""
    writer = csv.writer(sys.stdout, lineterminator='\n')
    writer.writerow(HEADER)
    for command, row in found:
        sys.stdout.write(f'# capture first: {command}\n')
        writer.writerow(row)


class Resolver:
    """The GitHub login of a commit author: the account GitHub links to the commit."""

    def __init__(self, session):
        self.session = session

    def __call__(self, email, entry, commit):
        query = ('query($owner: String!, $name: String!, $oid: GitObjectID!) { repository(owner: $owner, '
                 'name: $name) { object(oid: $oid) { ... on Commit { author { user { login } } } } } }')
        data = github_graphql(self.session, query, {'owner': plone_changelogs.ORGANISATION,
                                                    'name': entry.repository, 'oid': commit['sha']})
        user = (((data.get('repository') or {}).get('object') or {}).get('author') or {}).get('user')
        return user['login'] if user else None


def main():
    parser = argparse.ArgumentParser(description='List changelog names without a mapping (#71)')
    parser.add_argument('--from-year', type=int, default=changelogs.REPORTED_YEARS[0],
                        help=f'First year (default: {changelogs.REPORTED_YEARS[0]})')
    parser.add_argument('--to-year', type=int, default=changelogs.REPORTED_YEARS[-1],
                        help=f'Last year (default: {changelogs.REPORTED_YEARS[-1]})')
    parser.add_argument('--propose', action='store_true',
                        help='Propose people from the commits that repeat the entries (needs GITHUB_TOKEN); '
                             'prints the capture command and the identity row of each, writes nothing')
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

        rows = proposals(unmatched, evidence(unmatched, commits_of), Resolver(session), load_registry(),
                         args.min_share)
        print('\nProposals for identities.csv (check each, run its capture command, then add the row; the last '
              'three columns are not part of the file):')
        print_proposals(rows)


if __name__ == '__main__':
    main()
