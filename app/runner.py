
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass


@dataclass
class RunResult:
    status: str
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float


class DockerRunner:
    """Build and run a controlled test fixture with Docker."""

    IMAGE = "repocheck-fixture:dev"

    def __init__(self, timeout_seconds: int = 30) -> None:
        self.timeout_seconds = timeout_seconds

    def run_fixture(self) -> dict:
        """Build and execute the trusted sample test project."""
        start = time.monotonic()
        container_name = f"repocheck-{uuid.uuid4().hex[:12]}"

        try:
            build = subprocess.run(
                [
                    "docker", "build",
                    "--tag", self.IMAGE,
                    "fixtures/sample-python",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                shell=False,
            )

            if build.returncode != 0:
                return asdict(
                    RunResult(
                        status="build_failed",
                        exit_code=build.returncode,
                        stdout=build.stdout[-10000:],
                        stderr=build.stderr[-10000:],
                        duration_seconds=round(time.monotonic() - start, 3),
                    )
                )

            command = [
                "docker", "run",
                "--name", container_name,
                "--network", "none",
                "--memory", "128m",
                "--cpus", "0.5",
                "--pids-limit", "64",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--user", "10001:10001",
                self.IMAGE,
                "python", "-m", "pytest", "-v", "-p", "no:cacheprovider",
                "/workspace/test_math.py",
            ]

            try:
                run = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                    shell=False,
                )

                returncode = run.returncode
                status = "succeeded" if returncode == 0 else "failed"
                stdout = run.stdout[-10000:]
                stderr = run.stderr[-10000:]

            except subprocess.TimeoutExpired as exc:
                # Stop the container even if the Docker CLI timed out.
                subprocess.run(
                    ["docker", "kill", container_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    shell=False,
                )
                returncode = None
                status = "timeout"
                stdout = str(exc.stdout or "")[-10000:]
                stderr = str(exc.stderr or "")[-10000:]

            return asdict(
                RunResult(
                    status=status,
                    exit_code=returncode,
                    stdout=stdout,
                    stderr=stderr,
                    duration_seconds=round(time.monotonic() - start, 3),
                )
            )

        except subprocess.TimeoutExpired:
            return asdict(
                RunResult(
                    status="runner_error",
                    exit_code=None,
                    stdout="",
                    stderr="Docker build or cleanup timed out.",
                    duration_seconds=round(time.monotonic() - start, 3),
                )
            )
        except OSError as exc:
            return asdict(
                RunResult(
                    status="runner_error",
                    exit_code=None,
                    stdout="",
                    stderr=str(exc)[:1000],
                    duration_seconds=round(time.monotonic() - start, 3),
                )
            )
        finally:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                shell=False,
            )



'''
shell=False: Python doesn't invoke a shell to interpret the command.
--network none: the container has no external network access.
--read-only: the container's root filesystem cannot be modified.
--memory, --cpus, and --pids-limit: constrain resource consumption.
--cap-drop ALL and no-new-privileges: reduce container privileges.
--user 10001:10001: avoid running as root inside the container.
The command and image are fixed; no user-supplied command is accepted.
'''