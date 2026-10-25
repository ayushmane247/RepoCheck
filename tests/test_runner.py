
import subprocess
from pathlib import Path
from unittest.mock import patch

from app.runner import DockerRunner


def test_source_runner_keeps_restricted_docker_options(tmp_path):
    with patch("app.runner.subprocess.run") as mock_run:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=["docker", "run"], returncode=0, stdout="1 passed", stderr=""),
            subprocess.CompletedProcess(args=["docker", "rm"], returncode=0, stdout="", stderr=""),
        ]

        result = DockerRunner().run_source(Path(tmp_path))

    command = mock_run.call_args_list[0].args[0]
    assert result["status"] == "succeeded"
    assert "--network" in command and command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert "--memory" in command and "--cpus" in command and "--pids-limit" in command
    assert "--cap-drop" in command and command[command.index("--cap-drop") + 1] == "ALL"
    assert "no-new-privileges" in command
    assert "10001:10001" in command
    mount = command[command.index("--mount") + 1]
    assert mount.endswith("target=/workspace,readonly")


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
