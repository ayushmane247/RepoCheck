from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from app.analysis import analyze_readiness
from app.configuration import inspect_configuration
from app.detector import detect_support
from app.errors import (
    ArchiveDownloadError,
    GitHubRateLimitError,
    GitHubUnavailableError,
    RepositoryNotFoundError,
    UnsafeArchiveError,
)
from app.github_urls import parse_github_url
from app.inspector import inspect_repository
from app.runner import DockerRunner
from app.settings import ExecutionMode
from app.source_archive import (
    create_temporary_workspace,
    download_archive,
    extract_archive_safely,
)


def validate_repository(
    url: str,
    progress: Callable[[str], None] | None = None,
    *,
    execution_mode: ExecutionMode = ExecutionMode.LOCAL_DOCKER,
) -> dict:
    """Inspect a repository and execute tests only in local Docker mode."""
    def stage(message: str) -> None:
        if progress is not None:
            progress(message)

    owner, repository = parse_github_url(url)
    report = {
        "repository": f"{owner}/{repository}",
        "default_branch": None,
        "status": "error",  # Kept for clients using the original response.
        "execution_mode": execution_mode.value,
        "supported": False,
        "language": None,
        "framework": None,
        "test_files": [],
        "test_file_count": 0,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "duration_seconds": 0.0,
        "message": "Repository validation could not be completed.",
    }
    workspace: Path | None = None

    try:
        stage("Inspecting repository metadata on GitHub")
        metadata = inspect_repository(url)
        report["repository"] = metadata.get("repository", report["repository"])
        report["default_branch"] = metadata["default_branch"]

        workspace = create_temporary_workspace()
        stage("Downloading the repository source archive")
        archive_bytes = download_archive(
            owner, repository, metadata["default_branch"]
        )
        stage("Safely extracting repository files")
        source_root = extract_archive_safely(
            archive_bytes, workspace / "source"
        )
        stage("Checking setup, workflows, and supported test files")
        configuration = inspect_configuration(source_root)
        report["configuration"] = configuration["summary"]
        paths = [
            path.relative_to(source_root).as_posix()
            for path in source_root.rglob("*")
            if path.is_file() and not path.is_symlink()
        ]
        detection = detect_support(paths)
        report.update({
            "supported": detection["supported"],
            "language": detection.get("language"),
            "framework": detection.get("framework"),
            "test_files": detection["test_files"],
            "test_file_count": detection["test_file_count"],
        })

        if not detection["supported"]:
            stage("Preparing the unsupported-language findings")
            report["status"] = "unsupported"
            report["message"] = detection["reason"]
            report.update(analyze_readiness(detection, configuration=configuration))
            return report

        if execution_mode is ExecutionMode.INSPECTION_ONLY:
            stage("Inspection complete; detected tests were not run in hosted mode")
            report["status"] = "not_run"
            report["message"] = (
                "Repository inspection completed. Tests were not run by the hosted inspection-only service."
            )
            report["duration_seconds"] = None
            report.update(analyze_readiness(
                detection, configuration=configuration, tests_not_run=True
            ))
            stage("Preparing the inspection evidence")
            return report

        stage("Running detected tests in the restricted Docker runner")
        result = DockerRunner().run_source(source_root)
        runner_status = result.get("status")
        legacy_statuses = {
            "succeeded": "passed",
            "failed": "failed",
            "timeout": "timeout",
            "runner_error": "runner_error",
            "no_tests_collected": "no_tests_collected",
        }
        report["status"] = legacy_statuses.get(runner_status, "error")
        report.update({
            "exit_code": result.get("exit_code"),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "duration_seconds": result.get("duration_seconds", 0.0),
        })
        report.update(analyze_readiness(
            detection, result, configuration=configuration
        ))

        report["message"] = {
            "passed": "Python tests completed successfully.",
            "failed": "Test execution failed. Review the test output.",
            "timeout": "Test execution exceeded the configured time limit.",
            "runner_error": "The Docker runner could not execute the tests.",
            "no_tests_collected": "Pytest did not collect any tests from the detected files.",
            "error": "The test runner returned an unexpected result.",
        }[report["status"]]
        stage("Preparing the validation evidence")
        return report

    except (
        ValueError,
        RepositoryNotFoundError,
        GitHubRateLimitError,
        GitHubUnavailableError,
        ArchiveDownloadError,
        UnsafeArchiveError,
    ):
        raise
    except Exception:
        report["status"] = "error"
        report["message"] = "An unexpected error interrupted repository validation."
        report.update(analyze_readiness({}, validation_error=True))
        return report
    finally:
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)
