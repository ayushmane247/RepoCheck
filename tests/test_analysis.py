import pytest

from app.analysis import analyze_readiness


SUPPORTED = {"supported": True, "language": "python"}


@pytest.mark.parametrize(
    ("result", "expected_test", "expected_readiness", "expected_code"),
    [
        ({"status": "succeeded", "exit_code": 0}, "passed", "checks_passed", "TESTS_PASSED"),
        ({"status": "failed", "exit_code": 1}, "failed", "needs_attention", "TESTS_FAILED"),
        ({"status": "failed", "exit_code": 2, "stdout": "ERROR collecting tests/test_api.py"}, "collection_failed", "needs_attention", "TEST_COLLECTION_FAILED"),
        ({"status": "no_tests_collected", "exit_code": 5}, "no_tests", "not_assessed", "NO_TESTS_COLLECTED"),
        ({"status": "timeout", "exit_code": None}, "timed_out", "needs_attention", "TEST_TIMEOUT"),
        ({"status": "runner_error", "exit_code": None}, "runner_error", "needs_attention", "RUNNER_ERROR"),
    ],
)
def test_execution_outcomes_are_consistent(
    result, expected_test, expected_readiness, expected_code
):
    analysis = analyze_readiness(SUPPORTED, result)
    assert analysis["validation_status"] == "completed"
    assert analysis["test_status"] == expected_test
    assert analysis["readiness_assessment"] == expected_readiness
    assert analysis["findings"][0]["code"] == expected_code
    assert {"severity", "title", "message", "recommendation"} <= analysis["findings"][0].keys()


def test_no_supported_tests_produces_actionable_warning():
    analysis = analyze_readiness({"supported": False, "language": "python"})
    assert analysis["test_status"] == "no_tests"
    assert analysis["readiness_assessment"] == "not_assessed"
    assert analysis["findings"][0]["severity"] == "warning"
    assert analysis["findings"][0]["recommendation"]


def test_unsupported_language_is_not_reported_as_test_failure():
    analysis = analyze_readiness({
        "supported": False, "language": "javascript", "unsupported_language": True,
    })
    assert analysis["test_status"] == "unsupported"
    assert analysis["readiness_assessment"] == "not_assessed"
    assert analysis["findings"][0]["code"] == "UNSUPPORTED_LANGUAGE"


def test_unexpected_internal_error_is_incomplete_and_not_assessed():
    analysis = analyze_readiness({}, validation_error=True)
    assert analysis["validation_status"] == "failed"
    assert analysis["test_status"] == "incomplete"
    assert analysis["readiness_assessment"] == "not_assessed"
    assert analysis["findings"][0]["code"] == "VALIDATION_INCOMPLETE"


def test_unrecognized_runner_result_is_inconclusive():
    analysis = analyze_readiness(SUPPORTED, {"status": "future_status"})
    assert analysis["test_status"] == "incomplete"
    assert analysis["readiness_assessment"] == "not_assessed"
    assert analysis["findings"][0]["code"] == "TEST_RESULT_UNKNOWN"


def test_inspection_only_mode_reports_tests_not_run_without_assessment():
    analysis = analyze_readiness(SUPPORTED, tests_not_run=True)
    assert analysis["validation_status"] == "completed"
    assert analysis["test_status"] == "not_run"
    assert analysis["readiness_assessment"] == "not_assessed"
    assert analysis["findings"][0]["code"] == "TESTS_NOT_RUN"
    assert "did not execute" in analysis["findings"][0]["message"]


def test_optional_configuration_absence_does_not_fail_passing_tests():
    configuration = {
        "summary": {"status": "checked"},
        "findings": [{
            "code": "NO_GITHUB_ACTIONS_WORKFLOWS",
            "severity": "info",
            "title": "No GitHub Actions workflows found",
            "message": "No workflow files were found.",
            "recommendation": "Add one if CI is desired.",
        }],
    }
    analysis = analyze_readiness(
        SUPPORTED,
        {"status": "succeeded", "exit_code": 0},
        configuration=configuration,
    )
    assert analysis["test_status"] == "passed"
    assert analysis["configuration_status"] == "checked"
    assert analysis["readiness_assessment"] == "checks_passed"
    assert [finding["code"] for finding in analysis["findings"]] == [
        "TESTS_PASSED", "NO_GITHUB_ACTIONS_WORKFLOWS",
    ]
