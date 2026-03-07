#!/usr/bin/env python3
"""
Query GitHub API to get the full name of a user by their GitHub handle.
"""

import os
import requests
import sys
import time
from dotenv import load_dotenv

# Force reload environment
if 'GITHUB_TOKEN' in os.environ:
    del os.environ['GITHUB_TOKEN']
load_dotenv(override=True)

# Setup session with authentication
session = requests.Session()
token = os.getenv('GITHUB_TOKEN')
authenticated = False

if token:
    # Try Bearer format first (new tokens)
    session.headers.update({'Authorization': f'Bearer {token}'})
    test_response = session.get('https://api.github.com/user')

    if test_response.status_code == 200:
        authenticated = True
    else:
        # Try old token format
        session.headers.update({'Authorization': f'token {token}'})
        test_response = session.get('https://api.github.com/user')

        if test_response.status_code == 200:
            authenticated = True
        else:
            # Token doesn't work, proceed without authentication
            session.headers.pop('Authorization', None)
            print("Warning: GITHUB_TOKEN found but authentication failed. Using unauthenticated requests (lower rate limits).", file=sys.stderr)
else:
    print("Warning: No GITHUB_TOKEN found. Using unauthenticated requests (60 requests/hour limit).", file=sys.stderr)


def get_github_name(handle, debug=False):
    """
    Get the full name of a GitHub user by their handle.

    Args:
        handle: GitHub username/handle
        debug: If True, print debug information

    Returns:
        Full name of the user, or None if not found/not set
    """
    url = f"https://api.github.com/users/{handle}"

    try:
        response = session.get(url)

        if debug:
            print(f"Debug: Status code: {response.status_code}", file=sys.stderr)
            print(f"Debug: Headers: {response.headers}", file=sys.stderr)
            if response.status_code == 401:
                print(f"Debug: Token present: {bool(token)}", file=sys.stderr)
                print(f"Debug: Token length: {len(token) if token else 0}", file=sys.stderr)

        if response.status_code == 200:
            data = response.json()
            return data.get('name', None)
        elif response.status_code == 404:
            print(f"User '{handle}' not found", file=sys.stderr)
            return None
        elif response.status_code == 403:
            print(f"Rate limit exceeded. Try again later.", file=sys.stderr)
            return None
        else:
            print(f"Error: HTTP {response.status_code}", file=sys.stderr)
            if response.status_code == 401:
                print(f"Authentication failed. Check your GITHUB_TOKEN in .env file", file=sys.stderr)
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error querying GitHub API: {e}", file=sys.stderr)
        return None


def get_multiple_names(handles):
    """
    Get full names for multiple GitHub handles.

    Args:
        handles: List of GitHub handles or semicolon-separated string

    Returns:
        Dictionary mapping handles to names
    """
    # Handle semicolon-separated string
    if isinstance(handles, str):
        handles = [h.strip() for h in handles.split(';')]

    results = {}
    for handle in handles:
        if handle:
            name = get_github_name(handle)
            results[handle] = name
            # Be nice to the API - add a small delay between requests
            time.sleep(0.5)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_github_name.py <github_handle>")
        print("   or: python get_github_name.py <handle1> <handle2> ...")
        print("   or: python get_github_name.py --debug <handle>")
        sys.exit(1)

    debug = False
    handles = sys.argv[1:]

    # Check for debug flag
    if '--debug' in handles:
        debug = True
        handles.remove('--debug')

    if len(handles) == 1:
        # Single handle
        name = get_github_name(handles[0], debug=debug)
        if name:
            print(f"{handles[0]}: {name}")
        else:
            print(f"{handles[0]}: No name set or user not found")
    else:
        # Multiple handles
        results = get_multiple_names(handles)
        for handle, name in results.items():
            if name:
                print(f"{handle}: {name}")
            else:
                print(f"{handle}: No name set or user not found")
