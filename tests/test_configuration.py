from pathlib import Path

import pytest

from app.configuration import inspect_configuration


VALID_WORKFLOW = """name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest
"""


def test_reports_workflow_presence_and_conservative_structure(tmp_path):
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(VALID_WORKFLOW, encoding="utf-8")

    result = inspect_configuration(tmp_path)

    workflows = result["summary"]["workflows"]
    assert workflows["present"] is True
    assert workflows["count"] == 1
    assert workflows["files"] == [".github/workflows/ci.yml"]
    assert workflows["structural_status"] == "valid"
    assert workflows["checks"][0]["status"] == "valid"


def test_reports_no_workflows_without_marking_configuration_invalid(tmp_path):
    result = inspect_configuration(tmp_path)

    assert result["summary"]["workflows"]["present"] is False
    assert result["summary"]["workflows"]["structural_status"] == "not_found"
    assert result["summary"]["status"] == "checked"
    assert result["findings"][0]["code"] == "NO_GITHUB_ACTIONS_WORKFLOWS"
    assert result["findings"][0]["severity"] == "info"


@pytest.mark.parametrize("content", ["", "name: [unterminated", "name: CI\njobs: {}\n"])
def test_empty_malformed_or_incomplete_workflow_is_reported(tmp_path, content):
    workflow = tmp_path / ".github" / "workflows" / "ci.yaml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(content, encoding="utf-8")

    result = inspect_configuration(tmp_path)

    assert result["summary"]["workflows"]["structural_status"] == "invalid"
    finding = next(item for item in result["findings"] if item["code"] == "INVALID_GITHUB_ACTIONS_WORKFLOW")
    assert finding["severity"] == "warning"
    assert ".github/workflows/ci.yaml" in finding["message"]
    assert result["summary"]["status"] == "issues_found"


def test_reports_present_and_absent_python_config_and_manifests(tmp_path):
    absent = inspect_configuration(tmp_path)["summary"]
    assert absent["python_test_configuration"]["present"] is False
    assert absent["dependency_manifests"]["present"] is False

    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -q\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "sample"\n\n[tool.pytest.ini_options]\naddopts = "-q"\n',
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("pytest==8.4.2\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"dependencies": {}}\n', encoding="utf-8")

    summary = inspect_configuration(tmp_path)["summary"]
    assert summary["python_test_configuration"]["files"] == ["pytest.ini", "pyproject.toml"]
    assert summary["python_test_configuration"]["validity"] == {
        "pytest.ini": "valid", "pyproject.toml": "valid",
    }
    assert summary["dependency_manifests"]["files"] == [
        "requirements.txt", "pyproject.toml", "package.json",
    ]
    assert summary["dependency_manifests"]["syntax_status"]["requirements.txt"] == "not_checked"
    assert summary["dependency_manifests"]["dependency_resolution"] == "not_checked"


def test_malformed_pyproject_creates_one_combined_finding(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project\nname = 'broken'", encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest\naddopts = -q", encoding="utf-8")
    (tmp_path / "package.json").write_text("{not json}", encoding="utf-8")

    result = inspect_configuration(tmp_path)
    malformed_pyproject = [
        item for item in result["findings"]
        if item.get("file") == "pyproject.toml"
    ]
    assert len(malformed_pyproject) == 1
    assert set(malformed_pyproject[0]["roles"]) == {
        "python_test_configuration", "dependency_manifest",
    }
    assert any(item.get("file") == "pytest.ini" for item in result["findings"])
    assert any(item.get("file") == "package.json" for item in result["findings"])


def test_oversized_config_is_reported_without_reading_it(tmp_path, monkeypatch):
    import app.configuration as configuration

    monkeypatch.setattr(configuration, "MAX_CONFIG_BYTES", 3)
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    result = inspect_configuration(tmp_path)
    assert result["summary"]["status"] == "issues_found"
    assert any(
        finding["code"] == "INVALID_REPOSITORY_CONFIGURATION"
        for finding in result["findings"]
    )
