from urllib.parse import quote
from app.errors import (
    GitHubRateLimitError,
    GitHubUnavailableError,
    RepositoryNotFoundError,
)
import httpx


class GitHubClient:
    """Read-only client for GitHub's public REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=timeout,
            follow_redirects=False,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "RepoCheck/0.1.0",
            },
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _get_json(self, path: str) -> dict:
        """Request JSON from the GitHub API with basic error handling."""
        
        try:
            response = self._client.get(path)
        except httpx.TimeoutException as exc:
            raise GitHubUnavailableError(
                "GitHub API request timed out."
            ) from exc
        except httpx.RequestError as exc:
            raise GitHubUnavailableError(
                "Could not connect to the GitHub API."
            ) from exc

        if response.is_redirect:
            raise GitHubUnavailableError(
                "GitHub API redirects are not allowed."
            )

        if response.status_code == 404:
            raise RepositoryNotFoundError(
                "GitHub repository or resource not found."
            )

        if response.status_code == 403 and (
            "rate limit" in response.text.lower()
            or response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            raise GitHubRateLimitError("GitHub API rate limit exceeded.")

        if response.status_code >= 400:
            raise GitHubUnavailableError(
                f"GitHub API returned status {response.status_code}."
            )


        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError("GitHub API returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise ValueError("GitHub API returned an unexpected response.")

        return data

    def get_repository(self, owner: str, repository: str) -> dict:
        """Fetch metadata for a public repository."""
        return self._get_json(f"/repos/{owner}/{repository}")

    def get_tree(
        self, owner: str, repository: str, branch: str
    ) -> list[str]:
        """Return paths from the repository's recursive Git tree."""
        encoded_branch = quote(branch, safe="")
        data = self._get_json(
            f"/repos/{owner}/{repository}/git/trees/{encoded_branch}?recursive=1"
        )

        if data.get("truncated") is True:
            raise ValueError("GitHub returned a truncated repository tree.")

        tree = data.get("tree")
        if not isinstance(tree, list):
            raise ValueError("GitHub API returned an invalid repository tree.")

        paths = []
        for item in tree:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                paths.append(item["path"])

        return paths
