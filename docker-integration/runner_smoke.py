"""Explicit real-Docker smoke test for the reusable source runner.

Run after building the source image with:
    python -m pytest -q docker-integration/runner_smoke.py
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from app.runner import DockerRunner


def test_run_source_executes_a_temporary_pytest_project_in_docker() -> None:
    with TemporaryDirectory(prefix="repocheck-source-smoke-") as temporary:
        source_dir = Path(temporary)
        (source_dir / "test_runner_smoke.py").write_text(
            "from pathlib import Path\n"
            "\n"
            "def test_runs_from_read_only_source_mount():\n"
            "    assert Path.cwd() == Path('/workspace')\n"
            "    assert Path(__file__).parent == Path('/workspace')\n"
            "    assert 20 + 22 == 42\n",
            encoding="utf-8",
        )

        result = DockerRunner(timeout_seconds=60).run_source(source_dir)

    assert result["status"] == "succeeded", result
    assert result["exit_code"] == 0, result
    assert "1 passed" in result["stdout"], result
