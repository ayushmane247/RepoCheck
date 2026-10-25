
import subprocess
from unittest.mock import patch

from app.runner import DockerRunner


def test_fixture_run_succeeds():
    with patch("app.runner.subprocess.run") as mock_run:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "build"],
                returncode=0,
                stdout="Build complete",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["docker", "run"],
                returncode=0,
                stdout="2 passed",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["docker", "rm"],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        result = DockerRunner().run_fixture()

    assert result["status"] == "succeeded"
    assert result["exit_code"] == 0
    assert "2 passed" in result["stdout"]
    assert mock_run.call_count == 3


def test_fixture_build_failure():
    with patch("app.runner.subprocess.run") as mock_run:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "build"],
                returncode=1,
                stdout="",
                stderr="Build failed",
            ),
            subprocess.CompletedProcess(
                args=["docker", "rm"],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        result = DockerRunner().run_fixture()

    assert result["status"] == "build_failed"
    assert result["exit_code"] == 1


def test_fixture_timeout_kills_container():
    with patch("app.runner.subprocess.run") as mock_run:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["docker", "build"],
                returncode=0,
                stdout="Build complete",
                stderr="",
            ),
            subprocess.TimeoutExpired("docker run", 30),
            subprocess.CompletedProcess(
                args=["docker", "kill"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=["docker", "rm"],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        result = DockerRunner().run_fixture()

    assert result["status"] == "timeout"
    assert result["exit_code"] is None
