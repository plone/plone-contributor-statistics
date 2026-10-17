"""plone_pr_interactions.py uses the same repository selection as plone_contributors.py (#36)."""

from plone_contributors import EXCLUDED_REPOSITORIES_FILE
from plone_pr_interactions import PlonePRInteractionExtractor


class FakeResponse:
    status_code = 200

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def test_organization_repos_skip_excluded_and_keep_archived(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / EXCLUDED_REPOSITORIES_FILE).write_text(
        'repository,reason\ndockerhub-docs,Fork of docker-library/docs\n', encoding='utf-8'
    )
    pages = [
        [
            {'name': 'volto', 'archived': False},
            {'name': 'Products.TinyMCE', 'archived': True},
            {'name': 'dockerhub-docs', 'archived': False, 'fork': True},
        ],
        [],
    ]
    extractor = PlonePRInteractionExtractor(github_token='test-token')
    monkeypatch.setattr(extractor.session, 'get', lambda url, params=None: FakeResponse(pages[params['page'] - 1]))

    extractor.get_organization_repos()

    assert extractor.plone_repos == ['plone/volto', 'plone/Products.TinyMCE']
