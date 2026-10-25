
import httpx
import pytest

from app.errors import ArchiveDownloadError, UnsafeArchiveError
from app.source_archive import download_archive


def make_response(status_code, content=b"", headers=None):
    request = httpx.Request(
        "GET",
        "https://api.github.com/repos/owner/repo/zipball/main",
    )
    return httpx.Response(
        status_code,
        content=content,
        headers=headers,
        request=request,
    )


def test_downloads_archive_from_github(monkeypatch):
    def fake_stream(self, method, url):
        class Context:
            def __enter__(self):
                return make_response(200, b"zip-data")

            def __exit__(self, *args):
                pass

        return Context()

    monkeypatch.setattr(httpx.Client, "stream", fake_stream)

    assert download_archive("owner", "repo", "main") == b"zip-data"


def test_allows_redirect_to_codeload(monkeypatch):
    responses = [
        make_response(
            302,
            headers={"Location": "https://codeload.github.com/owner/repo/legacy.zip/refs/heads/main"},
        ),
        make_response(200, b"zip-data"),
    ]

    def fake_stream(self, method, url):
        class Context:
            def __enter__(self):
                response = responses.pop(0)
                response.request = httpx.Request("GET", url)
                return response

            def __exit__(self, *args):
                pass

        return Context()

    monkeypatch.setattr(httpx.Client, "stream", fake_stream)

    assert download_archive("owner", "repo", "main") == b"zip-data"
    assert responses == []


def test_rejects_redirect_to_unapproved_host(monkeypatch):
    def fake_stream(self, method, url):
        class Context:
            def __enter__(self):
                return make_response(
                    302,
                    headers={"Location": "https://evil.example/archive.zip"},
                )

            def __exit__(self, *args):
                pass

        return Context()

    monkeypatch.setattr(httpx.Client, "stream", fake_stream)

    with pytest.raises(ArchiveDownloadError, match="unapproved host"):
        download_archive("owner", "repo", "main")


def test_rejects_too_many_redirects(monkeypatch):
    def fake_stream(self, method, url):
        class Context:
            def __enter__(self):
                return make_response(
                    302,
                    headers={"Location": "https://api.github.com/redirect-again"},
                )

            def __exit__(self, *args):
                pass

        return Context()

    monkeypatch.setattr(httpx.Client, "stream", fake_stream)

    with pytest.raises(ArchiveDownloadError, match="Too many redirects"):
        download_archive("owner", "repo", "main")


def test_rejects_oversized_download(monkeypatch):
    import app.source_archive as source_archive

    monkeypatch.setattr(source_archive, "MAX_ARCHIVE_BYTES", 4)

    def fake_stream(self, method, url):
        class Context:
            def __enter__(self):
                return make_response(200, b"12345")

            def __exit__(self, *args):
                pass

        return Context()

    monkeypatch.setattr(httpx.Client, "stream", fake_stream)

    with pytest.raises(UnsafeArchiveError, match="25 MiB download limit"):
        download_archive("owner", "repo", "main")
