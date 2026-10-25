
import httpx
import pytest

from app.errors import (
    GitHubRateLimitError,
    GitHubUnavailableError,
    RepositoryNotFoundError,
)
from app.github_client import GitHubClient


def mock_response(status_code, json_data=None):
    return httpx.Response(
        status_code,
        json=json_data,
        request=httpx.Request("GET", "https://api.github.com/test"),
    )


def test_get_repository_returns_metadata(monkeypatch):
    def fake_get(self, url, **kwargs):
        return mock_response(
            200,
            {
                "full_name": "psf/requests",
                "default_branch": "main",
                "private": False,
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with GitHubClient() as client:
        result = client.get_repository("psf", "requests")

    assert result["full_name"] == "psf/requests"
    assert result["default_branch"] == "main"


def test_get_repository_raises_for_missing_repository(monkeypatch):
    def fake_get(self, url, **kwargs):
        return mock_response(404, {"message": "Not Found"})

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with GitHubClient() as client:
        with pytest.raises(RepositoryNotFoundError, match="not found"):
            client.get_repository("unknown", "missing")


def test_get_tree_returns_file_paths(monkeypatch):
    def fake_get(self, url, **kwargs):
        return mock_response(
            200,
            {
                "tree": [
                    {"path": "requirements.txt", "type": "blob"},
                    {"path": "app/main.py", "type": "blob"},
                    {"path": "src", "type": "tree"},
                ],
                "truncated": False,
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with GitHubClient() as client:
        result = client.get_tree("psf", "requests", "main")

    assert result == ["requirements.txt", "app/main.py", "src"]


def test_get_tree_rejects_truncated_results(monkeypatch):
    def fake_get(self, url, **kwargs):
        return mock_response(
            200,
            {
                "tree": [{"path": "requirements.txt", "type": "blob"}],
                "truncated": True,
            },
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with GitHubClient() as client:
        with pytest.raises(ValueError, match="truncated"):
            client.get_tree("psf", "requests", "main")


def test_redirects_are_rejected(monkeypatch):
    def fake_get(self, url, **kwargs):
        return httpx.Response(
            302,
            headers={"Location": "https://example.com"},
            request=httpx.Request("GET", "https://api.github.com/test"),
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with GitHubClient() as client:
        with pytest.raises(
            GitHubUnavailableError,
            match="redirects are not allowed",
        ):
            client.get_repository("psf", "requests")


def test_rate_limit_is_reported(monkeypatch):
    def fake_get(self, url, **kwargs):
        return httpx.Response(
            403,
            headers={"X-RateLimit-Remaining": "0"},
            json={"message": "API rate limit exceeded"},
            request=httpx.Request("GET", "https://api.github.com/test"),
        )

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    with GitHubClient() as client:
        with pytest.raises(
            GitHubRateLimitError,
            match="rate limit exceeded",
        ):
            client.get_repository("psf", "requests")
