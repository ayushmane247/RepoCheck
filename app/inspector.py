
from app.github_client import GitHubClient
from app.github_urls import parse_github_url


SUPPORTED_MANIFESTS = {
    "requirements.txt",
    "pyproject.toml",
    "package.json",
}


def inspect_repository(url: str) -> dict:
    """Inspect public repository metadata and detect supported manifests."""
    owner, repository = parse_github_url(url)

    with GitHubClient() as github:
        metadata = github.get_repository(owner, repository)
        default_branch = metadata.get("default_branch")

        if not isinstance(default_branch, str) or not default_branch:
            raise ValueError("GitHub repository has no valid default branch.")

        paths = github.get_tree(owner, repository, default_branch)

    manifests = sorted(
        path for path in paths
        if path.rsplit("/", 1)[-1] in SUPPORTED_MANIFESTS
    )

    return {
        "repository": metadata.get("full_name", f"{owner}/{repository}"),
        "description": metadata.get("description"),
        "default_branch": default_branch,
        "stars": metadata.get("stargazers_count", 0),
        "languages_url": metadata.get("languages_url"),
        "manifests": manifests,
        "manifest_count": len(manifests),
        "status": "manifests_found" if manifests else "no_supported_manifests",
    }
