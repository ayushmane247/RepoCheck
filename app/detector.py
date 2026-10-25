
from pathlib import PurePosixPath
from typing import Iterable


IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".tox",
    "build",
    "dist",
}

LANGUAGE_EXTENSIONS = {
    ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".java": "java", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php", ".cs": "csharp", ".cpp": "c++",
    ".c": "c", ".swift": "swift", ".kt": "kotlin",
}


def detect_support(paths: Iterable[str]) -> dict:
    """Find Python test files that RepoCheck can run with pytest."""
    test_files: set[str] = set()
    extensions: set[str] = set()

    for raw_path in paths:
        path = PurePosixPath(str(raw_path).replace("\\", "/"))

        if path.is_absolute() or ".." in path.parts:
            continue

        if any(part in IGNORED_PARTS for part in path.parts):
            continue

        extensions.add(path.suffix.lower())

        if path.suffix != ".py":
            continue

        if path.name.startswith("test_") or path.name.endswith("_test.py"):
            test_files.add(path.as_posix())

    results = sorted(test_files)
    supported = bool(results)
    language = (
        "python" if ".py" in extensions
        else next(
            (LANGUAGE_EXTENSIONS[suffix] for suffix in sorted(extensions)
             if suffix in LANGUAGE_EXTENSIONS),
            None,
        )
    )

    return {
        "supported": supported,
        "language": language,
        "framework": "pytest" if supported else None,
        "test_files": results,
        "test_file_count": len(results),
        "reason": (
            "Python test files detected."
            if supported
            else "No supported Python test files were detected."
        ),
        "unsupported_language": bool(language and language != "python"),
    }
