"""Volto test cases cut unchanged from tests/test_merge_commits.py and tests/test_pr_listing.py.

They use the fakes (FakeResponse, FakeSession, commit) of those files; archived, not run.
"""

from scripts.collect import volto_stats


def test_volto_skips_merge_commits(monkeypatch):
    monkeypatch.setattr(volto_stats.time, 'sleep', lambda seconds: None)
    session = FakeSession(FakeResponse([commit('2024-01-10', parents=2), commit('2024-02-01')]))

    assert volto_stats.get_commits(session, 'alice', '2024-01-01', '2024-12-31') == 1


def test_volto_counts_prs_by_merge_date():
    queries = []

    class SearchSession:
        def get(self, url, params=None, timeout=None):
            queries.append(params['q'])
            return FakeResponse({'total_count': 4})

    assert volto_stats.get_pull_requests(SearchSession(), 'alice', '2024-01-01', '2024-12-31') == 4
    assert 'merged:2024-01-01..2024-12-31' in queries[0]
    assert 'created:' not in queries[0]
