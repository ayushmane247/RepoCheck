"""Read repository configuration files without executing repository code."""

from __future__ import annotations

import configparser
import json
import tomllib
from pathlib import Path
from typing import Any

import yaml


MAX_CONFIG_BYTES = 1024 * 1024
PYTHON_CONFIG_FILES = ("pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg")
DEPENDENCY_MANIFESTS = ("requirements.txt", "pyproject.toml", "package.json")


def _read_text(path: Path) -> str:
    if path.stat().st_size > MAX_CONFIG_BYTES:
        raise ValueError("File exceeds RepoCheck's 1 MiB configuration limit.")
    return path.read_text(encoding="utf-8")


def _workflow_structure(document: Any) -> list[str]:
    """Check a small, documented subset of GitHub workflow structure."""
    problems: list[str] = []
    if not isinstance(document, dict):
        return ["The YAML document must be a mapping."]

    # PyYAML's YAML 1.1 resolver reads the unquoted GitHub key `on` as True.
    if "on" not in document and True not in document:
        problems.append("A top-level 'on' trigger is required.")

    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        problems.append("A non-empty top-level 'jobs' mapping is required.")
        return problems

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            problems.append(f"Job '{job_name}' must be a mapping.")
            continue
        if not isinstance(job.get("runs-on"), (str, list)) and not isinstance(
            job.get("uses"), str
        ):
            problems.append(
                f"Job '{job_name}' must declare 'runs-on' or reusable-workflow 'uses'."
            )
        steps = job.get("steps")
        if steps is not None and not isinstance(steps, list):
            problems.append(f"Job '{job_name}' steps must be a list.")
            continue
        if isinstance(steps, list):
            for index, step in enumerate(steps):
                if not isinstance(step, dict) or not (
                    isinstance(step.get("uses"), str)
                    or isinstance(step.get("run"), str)
                ):
                    problems.append(
                        f"Job '{job_name}' step {index + 1} must declare 'uses' or 'run'."
                    )
    return problems


def _parse_workflow(path: Path, repository_root: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(_read_text(path))
        problems = _workflow_structure(document)
    except Exception as exc:
        problems = [f"Could not parse workflow YAML: {str(exc)[:300]}"]
    return {
        "file": path.relative_to(repository_root).as_posix(),
        "status": "valid" if not problems else "invalid",
        "problems": problems,
    }


def _parse_ini(path: Path) -> str | None:
    parser = configparser.ConfigParser(
        interpolation=None,
        strict=True,
        allow_no_value=True,
    )
    try:
        parser.read_string(_read_text(path), source=path.as_posix())
    except Exception as exc:
        return str(exc)[:300]
    return None


def _parse_toml(path: Path) -> str | None:
    try:
        tomllib.loads(_read_text(path))
    except Exception as exc:
        return str(exc)[:300]
    return None


def _parse_json(path: Path) -> str | None:
    try:
        json.loads(_read_text(path))
    except Exception as exc:
        return str(exc)[:300]
    return None


def inspect_configuration(repository_root: Path) -> dict[str, Any]:
    """Summarize recognized workflow, pytest, and dependency configuration."""
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise ValueError("Repository source directory must exist.")

    workflow_dir = root / ".github" / "workflows"
    workflow_paths = sorted(
        (
            path for path in workflow_dir.rglob("*")
            if path.is_file() and not path.is_symlink()
            and path.suffix.lower() in {".yml", ".yaml"}
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    ) if workflow_dir.is_dir() and not workflow_dir.is_symlink() else []
    workflow_checks = [
        _parse_workflow(path, root) for path in workflow_paths
    ]

    python_config_paths = [
        root / name for name in PYTHON_CONFIG_FILES
        if (root / name).is_file() and not (root / name).is_symlink()
    ]
    config_errors: dict[str, str] = {}
    toml_path = root / "pyproject.toml"
    toml_error = _parse_toml(toml_path) if toml_path in python_config_paths else None
    if toml_error:
        config_errors["pyproject.toml"] = toml_error
    for path in python_config_paths:
        if path.name == "pyproject.toml":
            continue
        error = _parse_ini(path)
        if error:
            config_errors[path.name] = error

    manifest_paths = [
        root / name for name in DEPENDENCY_MANIFESTS
        if (root / name).is_file() and not (root / name).is_symlink()
    ]
    manifest_errors: dict[str, str] = {}
    for path in manifest_paths:
        if path.name == "pyproject.toml":
            error = toml_error
        elif path.name == "package.json":
            error = _parse_json(path)
        else:
            # Requirements syntax includes pip directives and is not evaluated.
            error = None
        if error:
            manifest_errors[path.name] = error

    findings: list[dict[str, Any]] = []
    if not workflow_checks:
        findings.append({
            "code": "NO_GITHUB_ACTIONS_WORKFLOWS",
            "severity": "info",
            "title": "No GitHub Actions workflows found",
            "message": "No .yml or .yaml files were found under .github/workflows/.",
            "recommendation": "Add a workflow if this repository should define GitHub Actions CI.",
        })
    for item in workflow_checks:
        if item["status"] == "invalid":
            findings.append({
                "code": "INVALID_GITHUB_ACTIONS_WORKFLOW",
                "severity": "warning",
                "title": "Workflow structure could not be validated",
                "message": f"{item['file']}: {' '.join(item['problems'])}",
                "recommendation": "Check YAML syntax and the documented workflow structure requirements.",
                "file": item["file"],
            })

    for filename in sorted(set(config_errors) | set(manifest_errors)):
        roles = []
        if filename in config_errors:
            roles.append("python_test_configuration")
        if filename in manifest_errors:
            roles.append("dependency_manifest")
        findings.append({
            "code": "INVALID_REPOSITORY_CONFIGURATION",
            "severity": "warning",
            "title": "Configuration file could not be parsed",
            "message": f"{filename}: {config_errors.get(filename) or manifest_errors[filename]}",
            "recommendation": "Correct the file's syntax; RepoCheck does not evaluate project configuration or resolve dependencies.",
            "file": filename,
            "roles": roles,
        })

    issues_found = bool(config_errors or manifest_errors) or any(
        item["status"] == "invalid" for item in workflow_checks
    )
    return {
        "summary": {
            "workflows": {
                "present": bool(workflow_checks),
                "count": len(workflow_checks),
                "files": [item["file"] for item in workflow_checks],
                "structural_status": (
                    "not_found" if not workflow_checks
                    else "invalid" if any(item["status"] == "invalid" for item in workflow_checks)
                    else "valid"
                ),
                "checks": workflow_checks,
            },
            "python_test_configuration": {
                "present": bool(python_config_paths),
                "files": [path.name for path in python_config_paths],
                "validity": {
                    path.name: "invalid" if path.name in config_errors else "valid"
                    for path in python_config_paths
                },
            },
            "dependency_manifests": {
                "present": bool(manifest_paths),
                "files": [path.name for path in manifest_paths],
                "syntax_status": {
                    path.name: "invalid" if path.name in manifest_errors
                    else "not_checked" if path.name == "requirements.txt"
                    else "valid"
                    for path in manifest_paths
                },
                "dependency_resolution": "not_checked",
            },
            "status": "issues_found" if issues_found else "checked",
        },
        "findings": findings,
    }
