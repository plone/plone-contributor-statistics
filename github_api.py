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
        reset = int(response.headers.get('X-RateLimit-Reset', 0))
        now = time.time() if now is None else now
        return max(reset - now, 0) + 1
    return None


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
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
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
