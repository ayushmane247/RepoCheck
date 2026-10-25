
import pytest

from app.github_urls import parse_github_url


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "https://github.com/psf/requests",
            ("psf", "requests"),
        ),
        (
            "https://github.com/owner-name/repo.name",
            ("owner-name", "repo.name"),
        ),
        (
            "https://github.com/owner/repo/",
            ("owner", "repo"),
        ),
    ],
)
def test_valid_github_urls(url, expected):
    assert parse_github_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/psf/requests",
        "https://github.com.evil.example/owner/repo",
        "https://user:pass@github.com/owner/repo",
        "https://github.com:8080/owner/repo",
        "https://github.com/owner",
        "https://github.com/owner/repo/issues",
        "not-a-url",
        "https://github.com/owner/repo?tab=readme",
        "https://github.com/owner/repo#readme",
        "https://github.com/owner/repo//",
        "https://github.com/owner/repo%2Fextra",
        "",
    ],
)
def test_invalid_github_urls(url):
    with pytest.raises(ValueError):
        parse_github_url(url)
