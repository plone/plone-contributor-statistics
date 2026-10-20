#!/usr/bin/env python3
"""Print the full name of GitHub users from the GitHub API (needs GITHUB_TOKEN for more than 60 requests an hour)."""

import argparse
import os
import sys
import time

import requests
from dotenv import load_dotenv

from scripts.lib.github_api import GitHubAPIError, github_get


def make_session():
    """A session with the token from GITHUB_TOKEN or .env, if there is one."""
    load_dotenv()
    session = requests.Session()
    token = os.getenv('GITHUB_TOKEN')
    if token:
        session.headers['Authorization'] = f'token {token}'
    else:
        print('Warning: no GITHUB_TOKEN found, using unauthenticated requests (60 requests/hour).', file=sys.stderr)
    return session


def get_github_name(session, handle, debug=False):
    """The full name of a GitHub user, or None when the user does not exist or has no name set."""
    url = f'https://api.github.com/users/{handle}'
    try:
        response = github_get(session, url)
    except GitHubAPIError as e:
        message = str(e)
        print(f"User '{handle}' not found" if 'HTTP 404' in message else f'Error: {message}', file=sys.stderr)
        return None
    if debug:
        print(f'Debug: status {response.status_code}, headers {response.headers}', file=sys.stderr)
    return response.json().get('name')


def get_multiple_names(session, handles, pause=0.5):
    """{handle: name} for several handles, with a pause between the requests."""
    results = {}
    for handle in handles:
        results[handle] = get_github_name(session, handle)
        time.sleep(pause)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description='Print the full name of GitHub users from the GitHub API.')
    parser.add_argument('handles', nargs='+', metavar='handle', help='GitHub login')
    parser.add_argument('--debug', action='store_true', help='print the API response')
    args = parser.parse_args(argv)
    session = make_session()
    if len(args.handles) == 1:
        results = {args.handles[0]: get_github_name(session, args.handles[0], debug=args.debug)}
    else:
        results = get_multiple_names(session, args.handles)
    for handle, name in results.items():
        print(f'{handle}: {name}' if name else f'{handle}: No name set or user not found')


if __name__ == '__main__':
    main()
