(function attachFeedback(root) {
  "use strict";

  function excerpt(report) {
    const output = [report.stdout, report.stderr].filter(Boolean).join("\n");
    return output.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).slice(-8).join("\n") || "No runner output was returned.";
  }

  function testCount(report) {
    const output = [report.stdout, report.stderr].filter(Boolean).join("\n");
    const match = output.match(/(?:^|\s)(\d+)\s+passed\b/i);
    return match ? Number(match[1]) : null;
  }

  function failureEvidence(report) {
    const output = [report.stdout, report.stderr].filter(Boolean).join("\n");
    const countMatch = output.match(/(?:^|\s)(\d+)\s+(?:failed|errors?)\b/i);
    const names = output.split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => /^(?:FAILED|ERROR)\s+\S+/.test(line))
      .slice(0, 5);
    const parts = [];
    if (countMatch) parts.push(`${countMatch[1]} failure${Number(countMatch[1]) === 1 ? "" : "s"} reported in pytest output.`);
    if (names.length) parts.push(`Reported test errors: ${names.join("; ")}.`);
    parts.push(`Captured output:\n${excerpt(report)}`);
    return parts.join(" ");
  }

  function contextFor(finding, report) {
    const files = Array.isArray(report.test_files) ? report.test_files : [];
    const count = testCount(report);
    const workflows = report.configuration && report.configuration.workflows;
    const manifests = report.configuration && report.configuration.dependency_manifests;
    switch (finding.code) {
      case "TESTS_PASSED":
        return { evidence: `${count === null ? "Pytest summary count was not present in the captured output." : `${count} test${count === 1 ? "" : "s"} passed, as reported in runner output.`}${files.length ? ` Detected test files: ${files.join(", ")}.` : ""}`, why: "Passing the tests RepoCheck collected is a useful signal for this checkout. It does not verify production behavior or tests that were not collected.", confidence: "Direct execution result", category: "Verified" };
      case "TESTS_FAILED":
        return { evidence: failureEvidence(report), why: "A non-zero test run means at least one collected check did not pass in this restricted environment.", confidence: "Direct execution result", category: "Verified" };
      case "TEST_COLLECTION_FAILED":
        return { evidence: excerpt(report), why: "Collection stopped before a valid test run, so the suite outcome is unknown.", confidence: "Direct runner output", category: "Verified" };
      case "TEST_TIMEOUT":
        return { evidence: `Runner status: ${report.test_status || report.status || "timed_out"}. ${excerpt(report)}`, why: "The configured time limit ended execution before RepoCheck could establish a test result.", confidence: "Direct runner result", category: "Verified" };
      case "RUNNER_ERROR":
        return { evidence: `Runner status: ${report.test_status || report.status || "runner_error"}. ${excerpt(report)}`, why: "Docker did not provide a test result, so this repository’s tests remain unjudged.", confidence: "Direct runner result", category: "Verified" };
      case "NO_SUPPORTED_TESTS":
        return { evidence: files.length ? files.join(", ") : "No matching pytest test files were reported by the detector.", why: "Without files matching the supported detection rules, RepoCheck cannot run this repository’s tests.", confidence: "Detector result", category: "Verified" };
      case "NO_TESTS_COLLECTED":
        return { evidence: excerpt(report), why: "Detected files did not yield collected pytest tests; a successful test run was not established.", confidence: "Direct runner output", category: "Verified" };
      case "UNSUPPORTED_LANGUAGE":
        return { evidence: `Detected language: ${report.language || "not reported"}. Supported runner: ${report.framework || "pytest"}.`, why: "RepoCheck currently runs Python tests only, so this repository was not executed.", confidence: "Detector result", category: "Verified" };
      case "NO_GITHUB_ACTIONS_WORKFLOWS":
        return { evidence: workflows && Array.isArray(workflows.files) ? `Inspected .github/workflows/: ${workflows.files.length ? workflows.files.join(", ") : "no .yml or .yaml workflow files found"}.` : "The configuration finding reports no workflow files in the inspected path.", why: "A repository-defined GitHub Actions workflow was not detected in the inspected path. Other CI systems and remote settings were not checked.", confidence: "Inspected paths only", category: "Verified" };
      case "INVALID_GITHUB_ACTIONS_WORKFLOW":
        return { evidence: finding.file || finding.message || "A workflow structural check reported an issue.", why: "The reported workflow did not satisfy the limited structural checks RepoCheck performs; this is not a full GitHub Actions validation.", confidence: "Static structure check", category: "Potential issue" };
      case "INVALID_REPOSITORY_CONFIGURATION":
        return { evidence: finding.file ? `${finding.file}: ${finding.message || "parse issue reported"}` : finding.message || "Configuration parse issue reported.", why: "A recognized configuration file could not be parsed, which may prevent tooling from reading its settings.", confidence: "Static parse check", category: "Potential issue" };
      case "VALIDATION_INCOMPLETE":
      case "TEST_RESULT_UNKNOWN":
        return { evidence: report.message || "The API did not return a conclusive execution result.", why: "RepoCheck cannot treat an unavailable or unexpected runner result as a successful test run.", confidence: "Incomplete result", category: "Not assessed" };
      default:
        return { evidence: finding.file || finding.message || "No additional evidence was included in the API response.", why: "RepoCheck reports only the information returned by its detector, configuration checks, and runner.", confidence: "API finding", category: finding.severity === "info" ? "Informational" : "Needs review" };
    }
  }

  function enrichFindings(report) {
    const items = Array.isArray(report.findings) ? report.findings : [];
    return items.map((finding) => Object.assign({}, finding, contextFor(finding, report)));
  }

  const api = { enrichFindings, testCount, failureEvidence };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.RepoCheckFeedback = api;
})(globalThis);
