"""Runtime settings that affect repository code execution."""

from enum import Enum


class ExecutionMode(str, Enum):
    LOCAL_DOCKER = "local_docker"
    INSPECTION_ONLY = "inspection_only"


def load_execution_mode(
    value: str | None, *, is_render: bool = False
) -> ExecutionMode:
    """Parse the mode, requiring an explicit value in Render deployments."""
    if value is None:
        if is_render:
            raise RuntimeError(
                "Missing required REPOCHECK_EXECUTION_MODE on Render; "
                "set it explicitly (normally to 'inspection_only')."
            )
        return ExecutionMode.LOCAL_DOCKER

    raw_value = value.strip()
    try:
        return ExecutionMode(raw_value)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in ExecutionMode)
        raise RuntimeError(
            f"Invalid REPOCHECK_EXECUTION_MODE {raw_value!r}; expected one of: {allowed}."
        ) from exc
