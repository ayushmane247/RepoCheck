
from unittest.mock import patch

from app.inspector import inspect_repository


def test_inspector_detects_supported_manifests():
    metadata = {
        "full_name": "owner/project",
        "description": "Test project",
        "default_branch": "main",
        "stargazers_count": 10,
        "languages_url": "https://api.github.com/repos/owner/project/languages",
    }
    paths = [
        "requirements.txt",
        "src/main.py",
        "frontend/package.json",
        "pyproject.toml",
        "README.md",
    ]

    with (
        patch("app.inspector.parse_github_url", return_value=("owner", "project")),
        patch("app.inspector.GitHubClient") as mock_client,
    ):
        mock_client.return_value.__enter__.return_value.get_repository.return_value = metadata
        mock_client.return_value.__enter__.return_value.get_tree.return_value = paths

        result = inspect_repository("https://github.com/owner/project")

    assert result["repository"] == "owner/project"
    assert result["manifest_count"] == 3
    assert result["manifests"] == [
        "frontend/package.json",
        "pyproject.toml",
        "requirements.txt",
    ]
    assert result["status"] == "manifests_found"


def test_inspector_reports_no_supported_manifests():
    metadata = {
        "full_name": "owner/project",
        "description": None,
        "default_branch": "main",
        "stargazers_count": 0,
        "languages_url": "https://api.github.com/repos/owner/project/languages",
    }

    with (
        patch("app.inspector.parse_github_url", return_value=("owner", "project")),
        patch("app.inspector.GitHubClient") as mock_client,
    ):
        mock_client.return_value.__enter__.return_value.get_repository.return_value = metadata
        mock_client.return_value.__enter__.return_value.get_tree.return_value = [
            "README.md",
            "src/main.py",
        ]

        result = inspect_repository("https://github.com/owner/project")

    assert result["manifests"] == []
    assert result["manifest_count"] == 0
    assert result["status"] == "no_supported_manifests"
