import sys
from pathlib import Path

import pytest

# The scripts run as modules from the repository root: python -m scripts.<stage>.<name>
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.lib import paths  # noqa: E402

# Header-only mapping files: the loaders require every file to exist
EMPTY_MAPPINGS = {
    paths.EXCLUDED_REPOSITORIES: 'repository,reason\n',
    paths.BOT_ACCOUNTS: 'login,reason\n',
    paths.COMMIT_AUTHORS: 'email,github_username,name,source\n',
    paths.ACCOUNT_ALIASES: 'alias,github_username,source\n',
    paths.CHANGELOG_NAMES: 'changelog_name,github_username,name,source\n',
    paths.FULLNAMES: 'github username,fullname,source\n',
}


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """An empty repository in tmp_path, as the current directory, with the folders and empty mapping files."""
    monkeypatch.chdir(tmp_path)
    for name, value in vars(paths).items():
        if isinstance(value, Path) and name.isupper():
            (value if not value.suffix else value.parent).mkdir(parents=True, exist_ok=True)
    for path, header in EMPTY_MAPPINGS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(header, encoding='utf-8')
    return tmp_path
