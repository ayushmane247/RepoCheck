
import io
import stat
import zipfile

import pytest

from app.errors import UnsafeArchiveError
from app.source_archive import extract_archive_safely


def make_zip(files: dict[str, str]) -> bytes:
    """Create an in-memory ZIP archive for tests."""
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)

    return buffer.getvalue()


def make_symlink_zip() -> bytes:
    """Create a ZIP archive containing a Unix symbolic-link entry."""
    buffer = io.BytesIO()

    info = zipfile.ZipInfo("repo-main/link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(info, "../outside.txt")

    return buffer.getvalue()


def test_extracts_valid_repository_archive(tmp_path):
    archive_bytes = make_zip({
        "repo-main/README.md": "RepoCheck",
        "repo-main/tests/test_math.py": (
            "def test_add():\n"
            "    assert 1 + 1 == 2\n"
        ),
    })

    root = extract_archive_safely(
        archive_bytes,
        tmp_path / "workspace",
    )

    assert root.name == "repo-main"
    assert (root / "README.md").read_text(encoding="utf-8") == "RepoCheck"
    assert (root / "tests" / "test_math.py").is_file()


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../escape.txt",
        "repo-main/../../escape.txt",
        "/absolute.txt",
        "repo-main\\..\\escape.txt",
    ],
)
def test_rejects_unsafe_paths(unsafe_path, tmp_path):
    archive_bytes = make_zip({unsafe_path: "malicious"})

    with pytest.raises(UnsafeArchiveError):
        extract_archive_safely(
            archive_bytes,
            tmp_path / "workspace",
        )

    assert not (tmp_path / "escape.txt").exists()


def test_rejects_multiple_repository_roots(tmp_path):
    archive_bytes = make_zip({
        "repo-one/README.md": "one",
        "repo-two/README.md": "two",
    })

    with pytest.raises(
        UnsafeArchiveError,
        match="exactly one repository root",
    ):
        extract_archive_safely(
            archive_bytes,
            tmp_path / "workspace",
        )


def test_rejects_invalid_zip(tmp_path):
    with pytest.raises(UnsafeArchiveError, match="Invalid ZIP"):
        extract_archive_safely(
            b"this is not a ZIP file",
            tmp_path / "workspace",
        )


def test_rejects_too_many_entries(tmp_path, monkeypatch):
    import app.source_archive as source_archive

    monkeypatch.setattr(
        source_archive,
        "MAX_ARCHIVE_FILES",
        2,
    )

    archive_bytes = make_zip({
        "repo-main/a.txt": "a",
        "repo-main/b.txt": "b",
        "repo-main/c.txt": "c",
    })

    with pytest.raises(UnsafeArchiveError, match="entries"):
        extract_archive_safely(
            archive_bytes,
            tmp_path / "workspace",
        )


def test_rejects_excessive_uncompressed_size(tmp_path, monkeypatch):
    import app.source_archive as source_archive

    monkeypatch.setattr(
        source_archive,
        "MAX_EXTRACTED_BYTES",
        10,
    )

    archive_bytes = make_zip({
        "repo-main/data.txt": "x" * 20,
    })

    with pytest.raises(UnsafeArchiveError, match="100 MiB limit"):
        extract_archive_safely(
            archive_bytes,
            tmp_path / "workspace",
        )


def test_rejects_symbolic_links(tmp_path):
    archive_bytes = make_symlink_zip()

    with pytest.raises(
        UnsafeArchiveError,
        match="link or special file",
    ):
        extract_archive_safely(
            archive_bytes,
            tmp_path / "workspace",
        )


def test_rejects_non_empty_destination_without_deleting_existing_files(
    tmp_path,
):
    destination = tmp_path / "workspace"
    destination.mkdir()

    important_file = destination / "keep.txt"
    important_file.write_text(
        "Do not delete this file.",
        encoding="utf-8",
    )

    archive_bytes = make_zip({
        "repo-main/test.py": "print('hello')",
    })

    with pytest.raises(
        UnsafeArchiveError,
        match="destination must be empty",
    ):
        extract_archive_safely(archive_bytes, destination)

    assert important_file.exists()
    assert important_file.read_text(encoding="utf-8") == (
        "Do not delete this file."
    )


def test_rejects_destination_that_is_a_file(tmp_path):
    destination = tmp_path / "workspace"
    destination.write_text("keep me", encoding="utf-8")

    archive_bytes = make_zip({
        "repo-main/README.md": "hello",
    })

    with pytest.raises(
        UnsafeArchiveError,
        match="must be a directory",
    ):
        extract_archive_safely(archive_bytes, destination)

    assert destination.read_text(encoding="utf-8") == "keep me"


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "repo-main/CON",
        "repo-main/NUL.txt",
        "repo-main/file.txt:stream",
        "repo-main/trailing-dot.",
        "repo-main/trailing-space ",
    ],
)
def test_rejects_windows_incompatible_filenames(unsafe_path, tmp_path):
    archive_bytes = make_zip({unsafe_path: "content"})

    with pytest.raises(UnsafeArchiveError):
        extract_archive_safely(
            archive_bytes,
            tmp_path / "workspace",
        )


def test_rejects_duplicate_paths(tmp_path):
    """Reject two ZIP entries with exactly the same path."""
    buffer = io.BytesIO()

    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("repo-main/README.md", "first")
            archive.writestr("repo-main/README.md", "second")

    with pytest.raises(
        UnsafeArchiveError,
        match="duplicate or conflicting",
    ):
        extract_archive_safely(
            buffer.getvalue(),
            tmp_path / "workspace",
        )


def test_rejects_case_colliding_paths(tmp_path):
    """Reject paths that collide on case-insensitive filesystems."""
    archive_bytes = make_zip({
        "repo-main/FILE.txt": "first",
        "repo-main/file.txt": "second",
    })

    with pytest.raises(
        UnsafeArchiveError,
        match="duplicate or conflicting",
    ):
        extract_archive_safely(
            archive_bytes,
            tmp_path / "workspace",
        )


def test_rejects_file_directory_collision(tmp_path):
    archive_bytes = make_zip({
        "repo-main/item": "this is a file",
        "repo-main/item/child.txt": (
            "this requires item to be a directory"
        ),
    })

    with pytest.raises(
        UnsafeArchiveError,
        match="conflicting file and directory",
    ):
        extract_archive_safely(
            archive_bytes,
            tmp_path / "workspace",
        )


def test_cleans_partial_extraction_after_failure(tmp_path, monkeypatch):
    import app.source_archive as source_archive

    destination = tmp_path / "workspace"
    archive_bytes = make_zip({
        "repo-main/first.txt": "first",
        "repo-main/second.txt": "second",
    })

    original_open = zipfile.ZipFile.open
    calls = 0

    def fail_on_second_file(self, name, *args, **kwargs):
        nonlocal calls

        if isinstance(name, zipfile.ZipInfo) and not name.is_dir():
            calls += 1

            if calls == 2:
                raise OSError("simulated extraction failure")

        return original_open(self, name, *args, **kwargs)

    monkeypatch.setattr(
        zipfile.ZipFile,
        "open",
        fail_on_second_file,
    )

    with pytest.raises(
        OSError,
        match="simulated extraction failure",
    ):
        source_archive.extract_archive_safely(
            archive_bytes,
            destination,
        )

    # The extractor created this directory, so it should remove it
    # when extraction fails.
    assert not destination.exists()


def test_rejects_high_compression_ratio(tmp_path, monkeypatch):
    import app.source_archive as source_archive

    monkeypatch.setattr(
        source_archive,
        "MAX_COMPRESSION_RATIO",
        2,
    )

    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "repo-main/data.txt",
            "A" * 10_000,
        )

    with pytest.raises(
        UnsafeArchiveError,
        match="suspicious compression ratio",
    ):
        extract_archive_safely(
            buffer.getvalue(),
            tmp_path / "workspace",
        )
