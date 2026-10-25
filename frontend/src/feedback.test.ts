import { describe, expect, it } from "vitest";
import { enrichFindings, testCount } from "./feedback";
import type { ValidationReport } from "./types";

const finding = (code: string, severity = "error") => ({ code, severity, title: code, message: "API message", recommendation: "API action" });

describe("evidence-backed finding feedback", () => {
  it("uses captured pytest count and detected paths for passing tests", () => {
    const report: ValidationReport = { test_files: ["tests/test_core.py"], stdout: "5 passed in 0.20s", findings: [finding("TESTS_PASSED", "info")] };
    const [item] = enrichFindings(report);
    expect(testCount(report)).toBe(5);
    expect(item.evidence).toContain("5 tests passed");
    expect(item.evidence).toContain("tests/test_core.py");
    expect(item.category).toBe("Verified");
  });

  it("includes failure count, failed test name, and captured output", () => {
    const [item] = enrichFindings({ stdout: "FAILED tests/test_math.py::test_sum - AssertionError\n1 failed", findings: [finding("TESTS_FAILED")] });
    expect(item.evidence).toContain("1 failure reported");
    expect(item.evidence).toContain("tests/test_math.py::test_sum");
    expect(item.why).toContain("non-zero test run");
  });

  it("keeps collection, timeout, runner, no-tests, and unsupported outcomes unjudged", () => {
    expect(enrichFindings({ stdout: "ERROR collecting tests/test_app.py", findings: [finding("TEST_COLLECTION_FAILED")] })[0].why).toContain("stopped before");
    expect(enrichFindings({ test_status: "timed_out", findings: [finding("TEST_TIMEOUT")] })[0].evidence).toContain("timed_out");
    expect(enrichFindings({ test_status: "runner_error", findings: [finding("RUNNER_ERROR")] })[0].why).toContain("remain unjudged");
    expect(enrichFindings({ test_files: [], findings: [finding("NO_SUPPORTED_TESTS")] })[0].evidence).toContain("No matching pytest test files");
    expect(enrichFindings({ language: "javascript", findings: [finding("UNSUPPORTED_LANGUAGE")] })[0].why).toContain("not executed");
  });

  it("describes the inspected workflow scope", () => {
    const [item] = enrichFindings({ configuration: { workflows: { files: [] } }, findings: [finding("NO_GITHUB_ACTIONS_WORKFLOWS", "info")] });
    expect(item.evidence).toContain(".github/workflows/");
    expect(item.why).toContain("Other CI systems and remote settings were not checked");
  });

  it("states directly that inspection-only tests were not executed", () => {
    const [item] = enrichFindings({ execution_mode: "inspection_only", test_status: "not_run", findings: [finding("TESTS_NOT_RUN", "info")] });
    expect(item.evidence).toContain("no runner was started");
    expect(item.why).toContain("cannot establish whether tests pass");
    expect(item.category).toBe("Not run");
  });
});
