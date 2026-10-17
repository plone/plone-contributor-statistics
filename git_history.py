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

The clones are bare and treeless: they only hold commits, not files. They
are kept in a cache directory and updated on the next run.
"""

import base64
import os
import re
import subprocess

# Release lines: 2.5, 3.0, 4.3.x, 6.0.x. Feature branches are unmerged work and are not counted.
VERSION_BRANCH = re.compile(r'^\d+(\.\d+)*(\.x)?$')
CACHE_DIR = os.path.join('.cache', 'repositories')

# Fields of a commit in the git log output. Dates are printed in UTC, like in the GitHub API.
_FIELDS = ['sha', 'parents', 'author_email', 'author_name', 'author_date', 'committer_date']
_FORMAT = '%x1f'.join(['%H', '%P', '%ae', '%an', '%ad', '%cd']) + '%x1e'
_DATE = '--date=format-local:%Y-%m-%dT%H:%M:%SZ'


class GitError(Exception):
    """A git command failed."""


def _git(*args, cwd=None, token=None):
    env = {**os.environ, 'TZ': 'UTC', 'GIT_TERMINAL_PROMPT': '0'}
    if token:
        # For private repositories. Passed in the environment, not on the command line.
        credentials = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
        env.update({'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'http.https://github.com/.extraheader',
                    'GIT_CONFIG_VALUE_0': f'Authorization: Basic {credentials}'})
    result = subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True, text=True, errors='replace')
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def update_clone(url, path, token=None):
    """Clone the repository into path, or fetch all branches if it is already there."""
    if os.path.isdir(path):
        # From origin, so that the treeless filter of the clone applies
        _git('fetch', '--quiet', '--prune', '--force', 'origin', '+refs/heads/*:refs/heads/*', cwd=path, token=token)
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
            },
            # Filled in from GitHub, see PloneStatsExtractor.link_authors
            'author': None,
        })
    return commits


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
    return commits + older
