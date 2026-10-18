"""GitHub API requests that wait for rate limits and fail loudly on errors.

Collectors must not record an API error as "no activity" (#41). Rate limits
are waited out and retried; every other error raises GitHubAPIError, so a
collection run stops instead of writing incomplete data.
"""

import time

import requests

# Responses that are not errors: 204 is returned for empty repositories by the
# contributors endpoint, 409 ("Git Repository is empty") by the commits endpoint.
EMPTY_STATUSES = (204, 409)

GRAPHQL_URL = 'https://api.github.com/graphql'
# GraphQL answers 502 when a query takes too long; a retry usually works
GRAPHQL_RETRY_STATUSES = (502, 503, 504)
CONNECTION_ERRORS = (requests.exceptions.ConnectionError,
                     requests.exceptions.Timeout,
                     requests.exceptions.ChunkedEncodingError)


def is_merge_commit(commit):
    """True for a merge commit (more than one parent), e.g. from GitHub's merge button.

    Merge commits are not code written by their author, so they are not
    counted as commits (#39).
    """
    return len(commit.get('parents', [])) > 1


class GitHubAPIError(Exception):
    """A GitHub API request failed and the data would be incomplete."""


def rate_limit_wait(response, now=None):
    """Return the seconds to wait if the response is a rate limit, else None."""
    if response.status_code not in (403, 429):
        return None
    retry_after = response.headers.get('Retry-After')
    if retry_after:
        return max(int(retry_after), 1)
    if response.headers.get('X-RateLimit-Remaining') == '0':
        return _reset_wait(response, now)
    return None


def _reset_wait(response, now=None):
    """Seconds until the rate limit of the response resets."""
    reset = int(response.headers.get('X-RateLimit-Reset', 0))
    now = time.time() if now is None else now
    return max(reset - now, 0) + 1


def github_get(session, url, params=None, max_retries=5, sleep=None):
    """GET a GitHub API URL.

    Returns the response for 200 and for empty repositories (see
    EMPTY_STATUSES). Waits and retries on rate limits and connection errors.
    Raises GitHubAPIError for anything else, or when retries are used up.
    """
    # Look up time.sleep at call time, so tests can replace it
    sleep = sleep or time.sleep
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, params=params, timeout=30)
        except CONNECTION_ERRORS as e:
            if attempt == max_retries:
                raise GitHubAPIError(f"{url}: {type(e).__name__} after {max_retries} attempts") from e
            sleep(2 ** attempt)
            continue

        if response.status_code == 200 or response.status_code in EMPTY_STATUSES:
            return response

        wait = rate_limit_wait(response)
        if wait is not None and attempt < max_retries:
            print(f"  Rate limit reached, waiting {int(wait)} seconds...")
            sleep(wait)
            continue

        raise GitHubAPIError(f"{url} (params {params}): HTTP {response.status_code} {response.text[:200]}")

    raise GitHubAPIError(f"{url}: still rate limited after {max_retries} attempts")


def github_graphql(session, query, variables=None, max_retries=5, sleep=None):
    """Run a GitHub GraphQL query and return its data.

    Waits and retries on rate limits, server errors and connection errors.
    Raises GitHubAPIError for errors in the response, or when retries are used up.
    """
    sleep = sleep or time.sleep
    for attempt in range(1, max_retries + 1):
        try:
            response = session.post(GRAPHQL_URL, json={'query': query, 'variables': variables or {}}, timeout=60)
        except CONNECTION_ERRORS as e:
            if attempt == max_retries:
                raise GitHubAPIError(f"GraphQL: {type(e).__name__} after {max_retries} attempts") from e
            sleep(2 ** attempt)
            continue

        wait = rate_limit_wait(response)
        if response.status_code == 200:
            errors = response.json().get('errors')
            if not errors:
                return response.json()['data']
            # A rate limit can also come as an error in a 200 response
            if not any(error.get('type') == 'RATE_LIMITED' for error in errors):
                raise GitHubAPIError(f"GraphQL errors (variables {variables}): {errors}")
            wait = _reset_wait(response)
        elif wait is None and response.status_code in GRAPHQL_RETRY_STATUSES:
            wait = 2 ** attempt

        if wait is not None and attempt < max_retries:
            print(f"  GraphQL: HTTP {response.status_code}, waiting {int(wait)} seconds...")
            sleep(wait)
            continue

        raise GitHubAPIError(f"GraphQL (variables {variables}): HTTP {response.status_code} {response.text[:200]}")

    raise GitHubAPIError(f"GraphQL: still failing after {max_retries} attempts")
