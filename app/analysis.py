"""Turn detected and executed checks into cautious readiness conclusions."""

from typing import Any


def _finding(
    code: str,
    severity: str,
    title: str,
    message: str,
    recommendation: str | None = None,
) -> dict[str, str | None]:
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "recommendation": recommendation,
    }


def _is_collection_failure(result: dict[str, Any]) -> bool:
    output = "\n".join(
        str(result.get(key) or "") for key in ("stdout", "stderr")
    ).lower()
    markers = (
        "error collecting ",
        "errors during collection",
        "interrupted: " ,
        "importerror while loading conftest",
    )
    return any(marker in output for marker in markers)


def analyze_readiness(
    detection: dict[str, Any],
    runner_result: dict[str, Any] | None = None,
    *,
    configuration: dict[str, Any] | None = None,
    validation_error: bool = False,
    tests_not_run: bool = False,
) -> dict[str, Any]:
    """Summarize only outcomes RepoCheck can directly verify."""
    findings: list[dict[str, Any]] = []
    configuration_summary = (configuration or {}).get("summary", {})
    configuration_status = configuration_summary.get("status", "not_checked")
    configuration_findings = (configuration or {}).get("findings", [])

    def readiness_for(test_status: str) -> str:
        if test_status in {"failed", "collection_failed", "timed_out", "runner_error"}:
            return "needs_attention"
        if configuration_status == "issues_found":
            return "needs_attention"
        if test_status == "passed":
            return "checks_passed"
        return "not_assessed"

    if validation_error:
        findings.append(_finding(
            "VALIDATION_INCOMPLETE", "error", "Validation was interrupted",
            "An unexpected internal error prevented RepoCheck from completing its checks.",
            "Review the RepoCheck service logs and retry validation.",
        ))
        return {
            "validation_status": "failed",
            "test_status": "incomplete",
            "readiness_assessment": "not_assessed",
            "configuration_status": configuration_status,
            "findings": findings,
        }

    if not detection.get("supported"):
        if detection.get("unsupported_language"):
            language = detection.get("language")
            findings.append(_finding(
                "UNSUPPORTED_LANGUAGE", "warning", "Repository language is unsupported",
                f"The detected primary source language is {language}; RepoCheck currently runs Python tests only.",
                "Use a Python repository or add support for this language's test runner.",
            ))
            test_status = "unsupported"
        else:
            findings.append(_finding(
                "NO_SUPPORTED_TESTS", "warning", "No supported Python tests detected",
                "RepoCheck did not find Python files matching its pytest test-file naming rules.",
                "Add pytest tests named test_*.py or *_test.py.",
            ))
            test_status = "no_tests"
        findings.extend(configuration_findings)
        return {
            "validation_status": "completed",
            "test_status": test_status,
            "readiness_assessment": readiness_for(test_status),
            "configuration_status": configuration_status,
            "findings": findings,
        }

    if tests_not_run:
        test_status = "not_run"
        findings.append(_finding(
            "TESTS_NOT_RUN", "info", "Tests were not run",
            "This hosted service inspected repository metadata and configuration only. It did not execute repository tests.",
            "Run the detected tests in a trusted local environment to establish their result.",
        ))
    elif runner_result is None:
        test_status = "incomplete"
        findings.append(_finding(
            "TEST_RESULT_UNKNOWN", "warning", "Test result is unavailable",
            "Supported tests were detected, but no execution result was available.",
            "Retry validation and check the runner service if this continues.",
        ))
    else:
        status = runner_result.get("status")
        exit_code = runner_result.get("exit_code")
        if status in {"no_tests_collected"} or exit_code == 5:
            test_status = "no_tests"
            findings.append(_finding(
                "NO_TESTS_COLLECTED", "warning", "Pytest collected no tests",
                "Test files were detected, but pytest did not collect any tests.",
                "Check test function and class names and pytest configuration.",
            ))
        elif status == "succeeded" and exit_code == 0:
            test_status = "passed"
            findings.append(_finding(
                "TESTS_PASSED", "info", "Detected tests passed",
                "All tests collected by the restricted pytest run passed. This does not establish overall production readiness.",
            ))
        elif status == "timeout":
            test_status = "timed_out"
            findings.append(_finding(
                "TEST_TIMEOUT", "error", "Test run timed out",
                "The test run exceeded RepoCheck's configured execution time limit.",
                "Investigate slow or blocked tests, then retry with an appropriate execution limit.",
            ))
        elif status == "runner_error":
            test_status = "runner_error"
            findings.append(_finding(
                "RUNNER_ERROR", "error", "Test runner could not execute",
                "Docker failed before RepoCheck could determine the test result.",
                "Check that Docker is running and the RepoCheck runner image is available.",
            ))
        elif _is_collection_failure(runner_result):
            test_status = "collection_failed"
            findings.append(_finding(
                "TEST_COLLECTION_FAILED", "error", "Pytest could not collect tests",
                "Pytest reported an import or collection error before running the test suite.",
                "Fix the reported import or collection error. Repository dependencies are not installed by RepoCheck.",
            ))
        elif status == "failed":
            test_status = "failed"
            findings.append(_finding(
                "TESTS_FAILED", "error", "Tests failed",
                "The restricted pytest run completed with one or more failures.",
                "Review the test output and fix the failing tests or required project setup.",
            ))
        else:
            test_status = "incomplete"
            findings.append(_finding(
                "TEST_RESULT_UNKNOWN", "warning", "Test result is inconclusive",
                "The runner returned an unrecognized result, so RepoCheck cannot determine whether tests passed.",
                "Review the runner output and retry validation.",
            ))

    findings.extend(configuration_findings)
    return {
        "validation_status": "completed",
        "test_status": test_status,
        "readiness_assessment": readiness_for(test_status),
        "configuration_status": configuration_status,
        "findings": findings,
    }
