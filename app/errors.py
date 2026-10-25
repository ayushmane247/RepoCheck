class RepositoryNotFoundError(Exception):
    """The requested public repository or resource does not exist."""


class GitHubRateLimitError(Exception):
    """GitHub API rate limit has been reached."""


class GitHubUnavailableError(Exception):
    """GitHub could not be reached or returned an upstream failure."""


class ArchiveDownloadError(Exception):
    """The source archive could not be downloaded."""


class UnsafeArchiveError(Exception):
    """The source archive violates RepoCheck's safety limits."""