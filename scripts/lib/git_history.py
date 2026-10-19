"""Read commit history from local clones of the repositories (#68).

The GitHub API lists the commits of one branch. In some repositories the
history from before the move to the egg structure is only on old release
branches: Products.CMFPlone's master starts in 2008, its branch 3.0 goes
back to 2002. Local clones can read all branches at once, and are faster
than the API.

Counted are the commits of the default branch, plus the commits of the
release branches that are older than the first commit of the default
branch. Later commits on release branches are mostly backports: the same
change as on the default branch, with another SHA. They are not counted
twice; the backport PRs are counted as PRs.

Commits that exist twice are counted once (#78):
- The "[fc]" commits in buildout.coredev are automatic copies of the
  commits in the core packages, under the original author's name.
- Within a repository, commits with the same author date and message are
  the same change with another SHA, e.g. a rebased branch that was merged
  as well, or SVN history that was imported twice.

The clones are bare and treeless: they only hold commits, not files. They
are kept in a cache directory and updated on the next run. The changelog
collector (#71) adds the trees of the branch tips and the few files it reads
to the same clones, see `files_at_tips`.
"""

import base64
import os
import re
import subprocess

# Release lines: 2.5, 3.0, 4.3.x, 6.0.x. Feature branches are unmerged work and are not counted.
VERSION_BRANCH = re.compile(r'^\d+(\.\d+)*(\.x)?$')
CACHE_DIR = os.path.join('.cache', 'repositories')

# Fields of a commit in the git log output. Dates are printed in UTC, like in the GitHub API.
_FIELDS = ['sha', 'parents', 'author_email', 'author_name', 'author_date', 'committer_date', 'subject']
_FORMAT = '%x1f'.join(['%H', '%P', '%ae', '%an', '%ad', '%cd', '%s']) + '%x1e'
_DATE = '--date=format-local:%Y-%m-%dT%H:%M:%SZ'


class GitError(Exception):
    """A git command failed."""


def _git(*args, cwd=None, token=None, binary=False, stdin=None):
    env = {**os.environ, 'TZ': 'UTC', 'GIT_TERMINAL_PROMPT': '0'}
    if token:
        # For private repositories. Passed in the environment, not on the command line.
        credentials = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
        env.update({'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraheader',
                    'GIT_CONFIG_VALUE_0': f'Authorization: Basic {credentials}'})
    if binary:
        result = subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True, input=stdin)
    else:
        result = subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True, text=True, errors='replace',
                                input=stdin)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors='replace') if binary else result.stderr
        raise GitError(f"git {' '.join(args[:6])}: {stderr.strip()}")
    return result.stdout


def update_clone(url, path, token=None, tags=False):
    """Clone the repository into path, or fetch all branches if it is already there.

    With `tags`, the tags are fetched as well; the changelog collector dates releases by them.
    """
    if os.path.isdir(path):
        # From origin, so that the treeless filter of the clone applies
        refspecs = ['+refs/heads/*:refs/heads/*'] + (['+refs/tags/*:refs/tags/*'] if tags else [])
        _git('fetch', '--quiet', '--prune', '--force', 'origin', *refspecs, cwd=path, token=token)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _git('clone', '--quiet', '--bare', '--filter=tree:0', url, path, token=token)
    return path


def release_branches(branches, default_branch):
    """The release branches, without the default branch."""
    return [b for b in branches if b != default_branch and VERSION_BRANCH.match(b)]


def list_branches(path):
    # Not %(refname:short): it gives "heads/3.0" when a tag has the same name
    refs = _git('for-each-ref', '--format=%(refname)', 'refs/heads', cwd=path).split()
    return [ref[len('refs/heads/'):] for ref in refs]


def read_commits(path, branches):
    """All commits reachable from the branches, each once, like the commit list of the GitHub API."""
    if not branches:
        return []
    # Full ref names: a tag can have the same name as a branch (3.0)
    refs = [f'refs/heads/{branch}' for branch in branches]
    output = _git('log', f'--format={_FORMAT}', _DATE, *refs, '--', cwd=path)
    commits = []
    for record in output.split('\x1e'):
        record = record.strip('\n')
        if not record:
            continue
        values = dict(zip(_FIELDS, record.split('\x1f')))
        commits.append({
            'sha': values['sha'],
            'parents': [{'sha': sha} for sha in values['parents'].split()],
            'commit': {
                'author': {'name': values['author_name'], 'email': values['author_email'],
                           'date': values['author_date']},
                'committer': {'date': values['committer_date']},
                'message': values['subject'],
            },
            # Filled in from GitHub, see PloneStatsExtractor.link_authors
            'author': None,
        })
    return commits


def is_copy(commit):
    """True for the automatic "[fc]" copies of core package commits in buildout.coredev."""
    return commit['commit']['message'].startswith('[fc]')


def without_duplicates(commits):
    """Drop copies, and commits with the same author date and message as an earlier one."""
    seen = set()
    result = []
    for commit in commits:
        key = (commit['commit']['author']['date'], commit['commit']['message'])
        if is_copy(commit) or key in seen:
            continue
        seen.add(key)
        result.append(commit)
    return result


def repository_commits(url, path, default_branch, token=None):
    """Update the clone and return the commits of the default branch, plus the older history of the release branches."""
    update_clone(url, path, token)
    branches = list_branches(path)
    if default_branch not in branches:  # empty repository
        return []

    commits = read_commits(path, [default_branch])
    # The dates have the same format, so they compare as strings
    first = min(commit['commit']['committer']['date'] for commit in commits)
    seen = {commit['sha'] for commit in commits}
    older = [
        commit for commit in read_commits(path, release_branches(branches, default_branch))
        if commit['sha'] not in seen and commit['commit']['committer']['date'] < first
    ]
    return without_duplicates(commits + older)


# Files at the branch tips (#71)

# Objects per fetch request, to keep the command line short
_FETCH_BATCH = 500


def branch_tips(path, branches):
    """{branch: commit} of the branches."""
    output = _git('for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', cwd=path)
    tips = dict(line.split(' ', 1) for line in output.splitlines())
    return {branch: tips[f'refs/heads/{branch}'] for branch in branches}


def _present_objects(path):
    """The objects that the clone has; listing them fetches nothing, unlike asking for one."""
    output = _git('cat-file', '--batch-all-objects', '--batch-check=%(objectname)', cwd=path)
    return set(output.split())


def _fetch_objects(path, oids, token=None):
    """Fetch objects by their ID, trees with all their subtrees, but without files.

    The negotiation is skipped: the clone has the commits, and the server
    would otherwise assume that it has their trees and files, too.
    """
    for start in range(0, len(oids), _FETCH_BATCH):
        _git('-c', 'fetch.negotiationAlgorithm=noop', 'fetch', '--quiet', '--no-tags', '--no-write-fetch-head',
             '--filter=blob:none', 'origin', *oids[start:start + _FETCH_BATCH], cwd=path, token=token)


def files_at_tips(path, branches, select, token=None):
    """The files at the tips of the branches whose path `select(path)` accepts.

    Returns {(branch, file path): (commit, content as bytes)}. Fetches the
    trees of the tips and the selected files into the treeless clone, only
    those it doesn't have yet.
    """
    if not branches:
        return {}
    tips = branch_tips(path, branches)
    present = _present_objects(path)
    roots = {branch: _git('rev-parse', f'{commit}^{{tree}}', cwd=path).strip() for branch, commit in tips.items()}
    missing = sorted({tree for tree in roots.values() if tree not in present})
    if missing:
        _fetch_objects(path, missing, token)

    wanted = {}
    for branch, commit in tips.items():
        for line in _git('ls-tree', '-r', '--full-tree', commit, cwd=path).splitlines():
            meta, name = line.split('\t', 1)
            _, kind, oid = meta.split()
            if kind == 'blob' and select(name):
                wanted[(branch, name)] = (commit, oid)

    blobs = sorted({oid for _, oid in wanted.values()})
    missing = [oid for oid in blobs if oid not in present]
    if missing:
        _fetch_objects(path, missing, token)
    contents = _read_blobs(path, blobs)
    return {key: (commit, contents[oid]) for key, (commit, oid) in wanted.items()}


def _read_blobs(path, oids):
    """{oid: content} from one `git cat-file --batch`."""
    if not oids:
        return {}
    output = _git('cat-file', '--batch', cwd=path, binary=True, stdin=('\n'.join(oids) + '\n').encode())
    contents = {}
    position = 0
    for oid in oids:
        end = output.index(b'\n', position)
        header = output[position:end].decode().split()
        if len(header) != 3:
            raise GitError(f'git cat-file: {oid} is missing')
        size = int(header[2])
        contents[header[0]] = output[end + 1:end + 1 + size]
        position = end + 1 + size + 1  # the content is followed by a newline
    return contents


def tag_dates(path):
    """{tag without a leading "v": date of the tag or of its commit as YYYY-MM-DD, in UTC}."""
    output = _git('for-each-ref', '--format=%(refname:strip=2)\t%(creatordate:format-local:%Y-%m-%d)',
                  'refs/tags', cwd=path)
    dates = {}
    for line in output.splitlines():
        tag, _, date = line.partition('\t')
        if date:
            dates.setdefault(tag[1:] if tag.startswith('v') else tag, date)
    return dates


def commit_messages(path, branches):
    """The full messages of the commits reachable from the branches: sha, author email and name, date, message."""
    if not branches:
        return []
    refs = [f'refs/heads/{branch}' for branch in branches]
    output = _git('log', '--no-merges', '--format=%H%x1f%ae%x1f%an%x1f%cd%x1f%B%x1e', _DATE, *refs, '--', cwd=path)
    commits = []
    for record in output.split('\x1e'):
        values = record.strip('\n').split('\x1f')
        if len(values) == 5:
            sha, email, name, date, message = values
            commits.append({'sha': sha, 'author_email': email, 'author_name': name, 'date': date,
                            'message': message})
    return commits
