import sys
from pathlib import Path

import pytest

# The scripts live in the repository root, not in a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paths  # noqa: E402

# Header-only mapping files: the loaders require every file to exist
EMPTY_MAPPINGS = {
    paths.EXCLUDED_REPOSITORIES: 'repository,reason\n',
    paths.BOT_ACCOUNTS: 'login,reason\n',
    paths.COMMIT_AUTHORS: 'email,github_username,name,source\n',
    paths.ACCOUNT_ALIASES: 'alias,github_username,source\n',
}


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """An empty repository in tmp_path, as the current directory, with empty mapping files."""
    monkeypatch.chdir(tmp_path)
    for path, header in EMPTY_MAPPINGS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(header, encoding='utf-8')
    return tmp_path
