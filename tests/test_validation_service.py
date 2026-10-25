from unittest.mock import patch

from app.validation_service import validate_repository


METADATA = {"repository": "owner/repo", "default_branch": "main"}
CONFIGURATION = {
    "summary": {"status": "checked"},
    "findings": [],
}


def test_unsupported_repository_returns_report(tmp_path):
    source = tmp_path / "source" / "repo-main"
    source.mkdir(parents=True)
    with (
        patch("app.validation_service.parse_github_url", return_value=("owner", "repo")),
        patch("app.validation_service.inspect_repository", return_value=METADATA),
        patch("app.validation_service.create_temporary_workspace", return_value=tmp_path),
        patch("app.validation_service.download_archive", return_value=b"archive"),
        patch("app.validation_service.extract_archive_safely", return_value=source),
        patch("app.validation_service.inspect_configuration", return_value=CONFIGURATION),
        patch("app.validation_service.detect_support", return_value={
            "supported": False, "framework": None, "test_files": [],
            "test_file_count": 0, "reason": "No supported Python test files were detected.",
        }),
    ):
        report = validate_repository("https://github.com/owner/repo")
    assert report["status"] == "unsupported"
    assert report["supported"] is False
    assert report["test_file_count"] == 0


def test_passed_tests_return_report(tmp_path):
    source = tmp_path / "source" / "repo-main"
    source.mkdir(parents=True)
    detected = {"supported": True, "framework": "pytest", "test_files": ["tests/test_x.py"], "test_file_count": 1, "reason": None}
    result = {"status": "succeeded", "exit_code": 0, "stdout": "1 passed", "stderr": "", "duration_seconds": 0.1}
    stages = []
    with (
        patch("app.validation_service.parse_github_url", return_value=("owner", "repo")),
        patch("app.validation_service.inspect_repository", return_value=METADATA),
        patch("app.validation_service.create_temporary_workspace", return_value=tmp_path),
        patch("app.validation_service.download_archive", return_value=b"archive"),
        patch("app.validation_service.extract_archive_safely", return_value=source),
        patch("app.validation_service.inspect_configuration", return_value={
            "summary": {"status": "issues_found"},
            "findings": [{
                "code": "INVALID_REPOSITORY_CONFIGURATION",
                "severity": "warning", "title": "Bad config",
                "message": "Configuration syntax is invalid.",
                "recommendation": "Fix its syntax.",
            }],
        }),
        patch("app.validation_service.detect_support", return_value=detected),
        patch("app.validation_service.DockerRunner.run_source", return_value=result),
    ):
        report = validate_repository("https://github.com/owner/repo", progress=stages.append)
    assert report["status"] == "passed"
    assert report["exit_code"] == 0
    assert report["test_status"] == "passed"
    assert report["configuration_status"] == "issues_found"
    assert report["readiness_assessment"] == "needs_attention"
    assert stages == [
        "Inspecting repository metadata on GitHub",
        "Downloading the repository source archive",
        "Safely extracting repository files",
        "Checking setup, workflows, and supported test files",
        "Running detected tests in the restricted Docker runner",
        "Preparing the validation evidence",
    ]
    assert [finding["code"] for finding in report["findings"]] == [
        "TESTS_PASSED", "INVALID_REPOSITORY_CONFIGURATION",
    ]
