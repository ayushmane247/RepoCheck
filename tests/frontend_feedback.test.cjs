const test = require("node:test");
const assert = require("node:assert/strict");
const { enrichFindings, testCount } = require("../frontend/feedback.js");

function finding(code, severity = "error") {
  return { code, severity, title: code, message: "API message", recommendation: "API action" };
}

test("successful pytest evidence uses the captured count and detected paths", () => {
  const [item] = enrichFindings({
    test_files: ["tests/test_core.py"], stdout: "5 passed in 0.20s", findings: [finding("TESTS_PASSED", "info")],
  });
  assert.equal(testCount({ stdout: "5 passed in 0.20s" }), 5);
  assert.match(item.evidence, /5 tests passed/);
  assert.match(item.evidence, /tests\/test_core.py/);
  assert.equal(item.category, "Verified");
});

test("failed tests show the reported count, test name, and captured output", () => {
  const [item] = enrichFindings({ stdout: "FAILED tests/test_math.py::test_sum - AssertionError\n1 failed", findings: [finding("TESTS_FAILED")] });
  assert.match(item.evidence, /1 failure reported/);
  assert.match(item.evidence, /tests\/test_math.py::test_sum/);
  assert.match(item.evidence, /FAILED tests\/test_math.py/);
  assert.match(item.why, /non-zero test run/);
});

test("collection, timeout, and Docker errors remain distinct incomplete outcomes", () => {
  const base = { stdout: "ERROR collecting tests/test_app.py", test_status: "collection_failed" };
  const [collection] = enrichFindings({ ...base, findings: [finding("TEST_COLLECTION_FAILED")] });
  const [timeout] = enrichFindings({ test_status: "timed_out", stdout: "time limit", findings: [finding("TEST_TIMEOUT")] });
  const [runner] = enrichFindings({ test_status: "runner_error", stderr: "Docker unavailable", findings: [finding("RUNNER_ERROR")] });
  assert.match(collection.why, /stopped before/);
  assert.match(timeout.evidence, /timed_out/);
  assert.match(runner.why, /remain unjudged/);
});

test("no tests and unsupported language do not claim a test pass", () => {
  const [none] = enrichFindings({ test_files: [], findings: [finding("NO_SUPPORTED_TESTS", "warning")] });
  const [unsupported] = enrichFindings({ language: "javascript", framework: null, findings: [finding("UNSUPPORTED_LANGUAGE", "warning")] });
  assert.match(none.evidence, /No matching pytest test files/);
  assert.match(unsupported.evidence, /javascript/);
  assert.match(unsupported.why, /not executed/);
});

test("workflow finding describes inspected paths and scope limitation", () => {
  const [item] = enrichFindings({
    configuration: { workflows: { files: [] } },
    findings: [finding("NO_GITHUB_ACTIONS_WORKFLOWS", "info")],
  });
  assert.match(item.evidence, /\.github\/workflows/);
  assert.match(item.why, /Other CI systems and remote settings were not checked/);
});
