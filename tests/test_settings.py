import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.settings import ExecutionMode, load_execution_mode


def test_execution_mode_defaults_to_local_docker_for_existing_development():
    assert load_execution_mode(None) is ExecutionMode.LOCAL_DOCKER


def test_missing_execution_mode_fails_on_render():
    with pytest.raises(
        RuntimeError,
        match="Missing required REPOCHECK_EXECUTION_MODE on Render.*inspection_only",
    ):
        load_execution_mode(None, is_render=True)


def test_explicit_inspection_only_mode_is_accepted_on_render():
    assert load_execution_mode("inspection_only", is_render=True) is ExecutionMode.INSPECTION_ONLY


def test_invalid_execution_mode_fails_closed_with_configuration_error():
    with pytest.raises(RuntimeError, match="Invalid REPOCHECK_EXECUTION_MODE.*local_docker, inspection_only"):
        load_execution_mode("docker_and_maybe_hosted")
    with pytest.raises(RuntimeError, match="Invalid REPOCHECK_EXECUTION_MODE"):
        load_execution_mode("")


def test_render_app_startup_rejects_missing_mode_before_app_creation():
    env = os.environ.copy()
    env.pop("REPOCHECK_EXECUTION_MODE", None)
    env["RENDER"] = "true"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.main; print('FASTAPI_APP_CREATED')",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Missing required REPOCHECK_EXECUTION_MODE on Render" in result.stderr
    assert "FASTAPI_APP_CREATED" not in result.stdout
