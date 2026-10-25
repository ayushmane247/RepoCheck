
from urllib.parse import urlsplit


def parse_github_url(url: str) -> tuple[str, str]:
    """Validate a public GitHub repository URL and return its owner and name."""
    if not url or not isinstance(url, str):
        raise ValueError("A GitHub repository URL is required.")

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid GitHub repository URL.") from exc

    if parsed.scheme != "https":
        raise ValueError("The URL must use HTTPS.")

    if parsed.hostname != "github.com":
        raise ValueError("The URL must use github.com.")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials are not allowed in the URL.")

    if port is not None:
        raise ValueError("Custom ports are not allowed.")

    if parsed.query or parsed.fragment:
        raise ValueError("Query strings and fragments are not allowed.")

    path = parsed.path
    
    if path.endswith("//") or path.startswith("//"):
        raise ValueError("Invalid repository path.")
    
    if "%2f" in path.lower() or "%5c" in path.lower():
        raise ValueError("Encoded path separators are not allowed.")
    
    parts = path.strip("/").split("/")

    if len(parts) != 2 or not all(parts):
        raise ValueError("The URL must identify exactly one owner and repository.")

    owner, repository = parts

    if owner in {".", ".."} or repository in {".", ".."}:
        raise ValueError("Invalid owner or repository name.")

    if any(char in owner + repository for char in "\\\x00"):
        raise ValueError("Invalid characters in owner or repository.")

    return owner, repository
