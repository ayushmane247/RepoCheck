
from __future__ import annotations

import io
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urljoin, urlsplit

import httpx

from app.errors import ArchiveDownloadError, UnsafeArchiveError


MAX_ARCHIVE_BYTES = 25 * 1024 * 1024  # 25 MiB
MAX_EXTRACTED_BYTES = 100 * 1024 * 1024  # 100 MiB
MAX_ARCHIVE_FILES = 2_000
MAX_COMPRESSION_RATIO = 200
CHUNK_SIZE = 64 * 1024

ALLOWED_ARCHIVE_HOSTS = {
    "api.github.com",
    "codeload.github.com",
}

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def _validate_archive_url(url: str) -> None:
    """Reject archive URLs outside the approved HTTPS GitHub hosts."""
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ArchiveDownloadError("Invalid archive URL.") from exc

    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_ARCHIVE_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise ArchiveDownloadError(
            "Archive URL uses an unapproved host or scheme."
        )


def download_archive(
    owner: str,
    repository: str,
    branch: str,
    *,
    timeout: float = 20.0,
) -> bytes:
    """Download a public GitHub ZIP archive with validated redirects."""
    url = (
        "https://api.github.com/repos/"
        f"{quote(owner, safe='')}/{quote(repository, safe='')}/zipball/"
        f"{quote(branch, safe='')}"
    )

    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "RepoCheck/0.1.0",
            },
        ) as client:
            for _ in range(4):
                _validate_archive_url(url)

                with client.stream("GET", url) as response:
                    if response.is_redirect:
                        location = response.headers.get("Location")
                        if not location:
                            raise ArchiveDownloadError(
                                "Archive redirect has no destination."
                            )

                        next_url = urljoin(url, location)
                        _validate_archive_url(next_url)
                        url = next_url
                        continue

                    if response.status_code == 404:
                        raise ArchiveDownloadError(
                            "Repository archive was not found."
                        )

                    if response.status_code >= 400:
                        raise ArchiveDownloadError(
                            f"Archive download returned HTTP "
                            f"{response.status_code}."
                        )

                    content_length = response.headers.get("Content-Length")
                    if content_length is not None:
                        try:
                            declared_size = int(content_length)
                        except ValueError as exc:
                            raise ArchiveDownloadError(
                                "Invalid archive Content-Length."
                            ) from exc

                        if declared_size < 0:
                            raise ArchiveDownloadError(
                                "Invalid archive Content-Length."
                            )

                        if declared_size > MAX_ARCHIVE_BYTES:
                            raise UnsafeArchiveError(
                                "Archive exceeds the 25 MiB download limit."
                            )

                    chunks: list[bytes] = []
                    total = 0

                    for chunk in response.iter_bytes(
                        chunk_size=CHUNK_SIZE
                    ):
                        total += len(chunk)
                        if total > MAX_ARCHIVE_BYTES:
                            raise UnsafeArchiveError(
                                "Archive exceeds the 25 MiB download limit."
                            )
                        chunks.append(chunk)

                    return b"".join(chunks)

            raise ArchiveDownloadError(
                "Too many redirects while downloading the archive."
            )

    except (ArchiveDownloadError, UnsafeArchiveError):
        raise
    except httpx.HTTPError as exc:
        raise ArchiveDownloadError(
            "Could not download the repository archive."
        ) from exc


def _validate_member_path(raw_name: str) -> PurePosixPath:
    """Validate a ZIP member path for safe cross-platform extraction."""
    if not raw_name or "\x00" in raw_name or "\\" in raw_name:
        raise UnsafeArchiveError("Archive contains an invalid path.")

    # ZIP paths use forward slashes. Reject absolute and drive-like paths.
    if raw_name.startswith("/") or raw_name.startswith("//"):
        raise UnsafeArchiveError("Archive contains an unsafe path.")

    relative = PurePosixPath(raw_name)

    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
        or ":" in relative.parts[0]
    ):
        raise UnsafeArchiveError("Archive contains an unsafe path.")

    for part in relative.parts:
        if any(ord(char) < 32 or ord(char) == 127 for char in part):
            raise UnsafeArchiveError(
                "Archive contains a control character in a path."
            )

        # Windows strips trailing dots/spaces and supports alternate data
        # streams using colons. Reject these to avoid cross-platform aliases.
        if part.endswith((".", " ")) or ":" in part:
            raise UnsafeArchiveError(
                "Archive contains a Windows-incompatible path."
            )

        # Windows reserves device names even when an extension is present.
        device_stem = part.split(".", 1)[0].upper()
        if device_stem in WINDOWS_RESERVED_NAMES:
            raise UnsafeArchiveError(
                "Archive contains a reserved Windows filename."
            )

    return relative


def _is_within(path: Path, parent: Path) -> bool:
    """Return whether path resolves within parent."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def extract_archive_safely(
    archive_bytes: bytes,
    destination: Path,
) -> Path:
    """
    Extract a GitHub ZIP archive into an empty, dedicated directory.

    Returns the repository root directory. Does not execute files or follow
    archive-provided links. On failure, removes extracted content created by
    this call while preserving a destination directory that already existed.
    """
    destination = Path(destination).resolve()
    destination_was_present = destination.exists()

    if destination_was_present:
        if not destination.is_dir():
            raise UnsafeArchiveError(
                "Extraction destination must be a directory."
            )
        if any(destination.iterdir()):
            raise UnsafeArchiveError(
                "Extraction destination must be empty."
            )
    else:
        destination.mkdir(parents=True, exist_ok=False)

    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except (zipfile.BadZipFile, OSError) as exc:
        if not destination_was_present:
            shutil.rmtree(destination, ignore_errors=True)
        raise UnsafeArchiveError("Invalid ZIP archive.") from exc

    try:
        with archive:
            entries = archive.infolist()

            if not entries:
                raise UnsafeArchiveError("Archive is empty.")

            if len(entries) > MAX_ARCHIVE_FILES:
                raise UnsafeArchiveError(
                    f"Archive contains more than {MAX_ARCHIVE_FILES} entries."
                )

            total_uncompressed = 0
            validated: list[tuple[zipfile.ZipInfo, PurePosixPath, bool]] = []
            root_names: set[str] = set()
            seen_paths: dict[str, bool] = {}

            for entry in entries:
                relative = _validate_member_path(entry.filename)
                is_directory = entry.is_dir()

                # Reject symlinks, devices, sockets, and other special files.
                unix_mode = (entry.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(unix_mode)

                if file_type not in {
                    0,
                    stat.S_IFREG,
                    stat.S_IFDIR,
                }:
                    raise UnsafeArchiveError(
                        "Archive contains a link or special file."
                    )

                if file_type == stat.S_IFDIR and not is_directory:
                    raise UnsafeArchiveError(
                        "Archive contains an inconsistent directory entry."
                    )

                if file_type == stat.S_IFREG and is_directory:
                    raise UnsafeArchiveError(
                        "Archive contains an inconsistent file entry."
                    )

                normalized = relative.as_posix().rstrip("/")
                collision_key = normalized.casefold()

                if collision_key in seen_paths:
                    raise UnsafeArchiveError(
                        "Archive contains duplicate or conflicting paths."
                    )

                # A file cannot also be a parent directory of another entry.
                for parent in relative.parents:
                    if parent == PurePosixPath("."):
                        continue
                    parent_key = parent.as_posix().casefold()
                    if seen_paths.get(parent_key) is False:
                        raise UnsafeArchiveError(
                            "Archive contains conflicting file and directory paths."
                        )

                # A new file cannot replace a directory already listed.
                if not is_directory:
                    prefix = collision_key + "/"
                    if any(key.startswith(prefix) for key in seen_paths):
                        raise UnsafeArchiveError(
                            "Archive contains conflicting file and directory paths."
                        )

                seen_paths[collision_key] = is_directory
                root_names.add(relative.parts[0])

                if entry.file_size < 0 or entry.compress_size < 0:
                    raise UnsafeArchiveError(
                        "Archive contains an invalid file size."
                    )

                total_uncompressed += entry.file_size
                if total_uncompressed > MAX_EXTRACTED_BYTES:
                    raise UnsafeArchiveError(
                        "Extracted archive would exceed the 100 MiB limit."
                    )

                if entry.file_size > 0:
                    if entry.compress_size == 0:
                        raise UnsafeArchiveError(
                            "Archive contains a suspicious compression ratio."
                        )
                    if (
                        entry.file_size / entry.compress_size
                        > MAX_COMPRESSION_RATIO
                    ):
                        raise UnsafeArchiveError(
                            "Archive contains a suspicious compression ratio."
                        )

                validated.append((entry, relative, is_directory))

            if len(root_names) != 1:
                raise UnsafeArchiveError(
                    "Archive must contain exactly one repository root folder."
                )

            root_name = next(iter(root_names))
            written_bytes = 0

            for entry, relative, is_directory in validated:
                target = (destination / Path(*relative.parts)).resolve()

                if not _is_within(target, destination):
                    raise UnsafeArchiveError(
                        "Archive path escapes the extraction directory."
                    )

                if is_directory:
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)

                # Exclusive creation prevents silently overwriting a file.
                with archive.open(entry, "r") as source:
                    with target.open("xb") as output:
                        while True:
                            chunk = source.read(CHUNK_SIZE)
                            if not chunk:
                                break

                            written_bytes += len(chunk)
                            if written_bytes > MAX_EXTRACTED_BYTES:
                                raise UnsafeArchiveError(
                                    "Extracted content exceeded the 100 MiB limit."
                                )

                            output.write(chunk)

            root = (destination / root_name).resolve()
            if not _is_within(root, destination) or not root.is_dir():
                raise UnsafeArchiveError(
                    "Archive repository root is missing or invalid."
                )

            return root

    except Exception:
        # The destination was verified empty before we started. Remove only
        # content created by this call; preserve a caller-owned empty directory.
        for child in destination.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass

        if not destination_was_present:
            shutil.rmtree(destination, ignore_errors=True)

        raise


def create_temporary_workspace() -> Path:
    """Create a unique temporary workspace for one repository run."""
    return Path(tempfile.mkdtemp(prefix="repocheck-"))
