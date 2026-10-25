const scenes = [...document.querySelectorAll(".scene")];
const briefing = document.querySelector("#briefing-screen");
const analysisScreen = document.querySelector("#analysis-screen");
const form = document.querySelector("#validate-form");
const urlInput = document.querySelector("#repo-url");
const submitButton = document.querySelector("#submit-button");
const formError = document.querySelector("#form-error");
const loadingPanel = document.querySelector("#analysis-loading");
const errorPanel = document.querySelector("#analysis-error");
const missionReport = document.querySelector("#mission-report");
const findingsList = document.querySelector("#findings-list");
const copyFeedback = document.querySelector("#copy-feedback");
let latestReport = null;
let latestUrl = "";
let displayedFindings = [];
let activeFilter = "all";
let feedbackTimer = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function showScene(id) {
  scenes.forEach((scene) => {
    const active = scene.id === id;
    scene.hidden = !active;
    scene.classList.toggle("is-active", active);
  });
  if (id === "analysis-screen") document.querySelector("#analysis-title").focus({ preventScroll: true });
}

function statusText(value) {
  return value ? String(value).replaceAll("_", " ") : "not reported";
}

document.querySelector("#get-started").addEventListener("click", () => {
  showScene("briefing-screen");
  urlInput.focus({ preventScroll: true });
});
document.querySelector("#skip-intro").addEventListener("click", () => {
  showScene("briefing-screen");
  urlInput.focus({ preventScroll: true });
});
document.querySelector("#back-to-intro").addEventListener("click", () => showScene("intro-screen"));
document.querySelectorAll("[data-scene-link]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    showScene(link.dataset.sceneLink);
  });
});

function displayRequestError(message) {
  loadingPanel.hidden = true;
  missionReport.hidden = true;
  errorPanel.hidden = false;
  document.querySelector("#error-message").textContent = `No validation report was returned, so the repository remains unjudged. ${message}`;
  document.querySelector("#error-message").focus({ preventScroll: true });
}

function responseError(body, status) {
  const detail = body && body.detail;
  if (typeof detail === "string") return `HTTP ${status}: ${detail}`;
  if (Array.isArray(detail)) return `HTTP ${status}: ${detail.map((item) => item.msg || "Invalid request").join("; ")}`;
  if (status === 429) return "GitHub rate limited the inspection request. Wait briefly and retry.";
  return `RepoCheck returned HTTP ${status}. The repository has not been assessed.`;
}

async function runAnalysis(repositoryUrl) {
  latestUrl = repositoryUrl;
  submitButton.disabled = true;
  analysisScreen.setAttribute("aria-busy", "true");
  formError.hidden = true;
  formError.textContent = "";
  showScene("analysis-screen");
  loadingPanel.hidden = false;
  errorPanel.hidden = true;
  missionReport.hidden = true;
  document.querySelector("#analysis-repository").textContent = repositoryUrl;
  document.querySelector("#loading-message").textContent = "RepoCheck is working through the request. The API returns a final result when its checks finish.";

  try {
    const response = await fetch("/repositories/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ url: repositoryUrl }),
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(responseError(body, response.status));
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      throw new Error("The API response was not a validation report.");
    }
    latestReport = body;
    renderReport(body, repositoryUrl);
  } catch (error) {
    displayRequestError(error instanceof TypeError
      ? "RepoCheck's API could not be reached. Check the service connection and retry."
      : error.message || "The request could not be completed.");
  } finally {
    submitButton.disabled = false;
    analysisScreen.removeAttribute("aria-busy");
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (submitButton.disabled) return;
  const repositoryUrl = urlInput.value.trim();
  if (!repositoryUrl || !urlInput.checkValidity()) {
    formError.hidden = false;
    formError.textContent = "Enter a valid HTTPS GitHub repository URL, such as https://github.com/owner/repo.";
    urlInput.focus();
    return;
  }
  runAnalysis(repositoryUrl);
});

document.querySelector("#retry-analysis").addEventListener("click", () => {
  if (latestUrl) runAnalysis(latestUrl);
});
document.querySelector("#edit-repository").addEventListener("click", () => {
  showScene("briefing-screen");
  urlInput.focus({ preventScroll: true });
});
document.querySelectorAll("#new-analysis, #run-again").forEach((button) => {
  button.addEventListener("click", () => {
    formError.hidden = true;
    showScene("briefing-screen");
    urlInput.focus({ preventScroll: true });
  });
});

function resultState(data) {
  if (data.validation_status === "failed") return "error";
  if (["failed", "collection_failed", "timed_out", "runner_error"].includes(data.test_status)) return "failure";
  if (data.readiness_assessment === "checks_passed") return "success";
  if (data.configuration_status === "issues_found") return "warning";
  return "partial";
}

function stateLabel(state) {
  return ({ success: "CHECKS PASSED", failure: "TESTS NEED ATTENTION", warning: "CONFIGURATION NEEDS REVIEW", error: "INSPECTION INCOMPLETE", partial: "PARTIAL READOUT" })[state];
}

function setText(id, value) {
  document.querySelector(`#${id}`).textContent = value;
}

function renderReport(data, requestedUrl) {
  loadingPanel.hidden = true;
  errorPanel.hidden = true;
  missionReport.hidden = false;
  const state = resultState(data);
  missionReport.dataset.state = state;
  document.querySelector("#report-eyebrow").textContent = `MISSION REPORT / ${stateLabel(state)}`;
  const titles = {
    success: "The supported checks came back clean.",
    failure: "We found something that needs your attention.",
    warning: "This setup could use a closer look.",
    error: "The inspection did not complete.",
    partial: "Some of this repository remains unjudged.",
  };
  setText("report-title", titles[state]);
  setText("report-message", data.message || "The API returned a validation report.");
  setText("report-announcement", `Mission report ready. Validation ${statusText(data.validation_status)}. Tests ${statusText(data.test_status)}. Readiness ${statusText(data.readiness_assessment)}.`);
  setText("analysis-repository", data.repository || requestedUrl);
  setText("repository-value", data.repository || requestedUrl);
  setText("validation-value", statusText(data.validation_status));
  setText("test-value", statusText(data.test_status));
  setText("readiness-value", statusText(data.readiness_assessment));
  setText("configuration-value", statusText(data.configuration_status));
  document.querySelector("#validation-value").dataset.state = data.validation_status || "";
  document.querySelector("#test-value").dataset.state = data.test_status || "";
  document.querySelector("#readiness-value").dataset.state = data.readiness_assessment || "";
  document.querySelector("#configuration-value").dataset.state = data.configuration_status || "";
  setText("branch-value", data.default_branch || "not reported");
  setText("language-value", [data.language, data.framework].filter(Boolean).join(" / ") || "not reported");
  setText("test-count-value", Number.isFinite(data.test_file_count) ? String(data.test_file_count) : "not reported");
  setText("exit-code-value", data.exit_code === null || data.exit_code === undefined ? "not returned" : String(data.exit_code));
  setText("duration-value", Number.isFinite(data.duration_seconds) ? `${data.duration_seconds.toFixed(2)} s` : "not reported");
  const seal = document.querySelector("#verdict-seal span");
  seal.textContent = state === "success" ? "✓" : state === "warning" || state === "partial" ? "!" : "×";
  renderFindings(data);
  renderConfiguration(data.configuration);
  renderLogs(data);
  copyFeedback.textContent = "";
  missionReport.querySelector("#report-title").focus({ preventScroll: true });
}

function appendFinding(finding) {
  const details = element("details", "finding-row");
  details.dataset.severity = finding.severity || "info";
  const summary = element("summary", "finding-summary");
  const severity = element("span", "finding-severity", finding.severity || "info");
  severity.dataset.severity = finding.severity || "info";
  const title = element("span", "finding-heading");
  title.append(element("strong", "finding-title", finding.title || "Finding"), element("small", "finding-code", finding.code || ""));
  summary.append(severity, title, element("span", "finding-chevron", "＋"));
  const body = element("div", "finding-detail");
  const inner = element("div", "finding-detail-inner");
  if (finding.message) appendFindingField(inner, "Finding", finding.message);
  appendFindingField(inner, "Evidence", finding.evidence || "No additional evidence was included in the API response.");
  if (finding.why) appendFindingField(inner, "Why it matters", finding.why);
  if (finding.file) appendFindingField(inner, "Path", finding.file, true);
  if (finding.recommendation) appendFindingField(inner, "Recommended action", finding.recommendation);
  appendFindingField(inner, "Confidence / limitation", [finding.category, finding.confidence].filter(Boolean).join(" · ") || "Based on the API finding.");
  body.append(inner);
  details.append(summary, body);
  findingsList.append(details);
}

function appendFindingField(parent, label, value, monospace = false) {
  const row = element("p", monospace ? "finding-field mono" : "finding-field");
  row.append(element("strong", "", `${label}: `), document.createTextNode(value));
  parent.append(row);
}

function renderFindings(data) {
  clear(findingsList);
  const findings = Array.isArray(data.findings) ? data.findings : [];
  displayedFindings = window.RepoCheckFeedback
    ? window.RepoCheckFeedback.enrichFindings({ ...data, findings })
    : findings;
  activeFilter = "all";
  document.querySelectorAll(".filter-button").forEach((button) => {
    button.classList.toggle("is-selected", button.dataset.filter === "all");
    button.setAttribute("aria-pressed", String(button.dataset.filter === "all"));
  });
  updateFindingFilter();
}

function updateFindingFilter() {
  clear(findingsList);
  const filtered = displayedFindings.filter((finding) => activeFilter === "all" || finding.severity === activeFilter);
  setText("finding-count", `${filtered.length}${filtered.length !== displayedFindings.length ? ` / ${displayedFindings.length}` : ""}`);
  if (!filtered.length) {
    findingsList.append(element("p", "empty-state", displayedFindings.length ? "No findings in this severity group." : "The API returned no findings."));
    return;
  }
  filtered.forEach(appendFinding);
}

document.querySelectorAll(".filter-button").forEach((button) => {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    document.querySelectorAll(".filter-button").forEach((item) => {
      const selected = item === button;
      item.classList.toggle("is-selected", selected);
      item.setAttribute("aria-pressed", String(selected));
    });
    updateFindingFilter();
  });
});

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function renderConfigGroup(parent, title, entries, absentText) {
  const group = element("section", "config-group");
  group.append(element("h3", "", title));
  if (!Array.isArray(entries) || !entries.length) {
    group.append(element("p", "empty-state", absentText));
  } else {
    const list = element("ul");
    entries.forEach((entry) => {
      const row = element("li");
      row.append(element("code", "mono", entry.file), element("span", `config-status status-${String(entry.status || "found").replaceAll("_", "-")}`, statusText(entry.status || "found")));
      list.append(row);
    });
    group.append(list);
  }
  parent.append(group);
}

function renderConfiguration(configuration) {
  const container = document.querySelector("#configuration-details");
  clear(container);
  if (!configuration || typeof configuration !== "object") {
    container.append(element("p", "empty-state", "Configuration details were not included in the API response."));
    return;
  }
  const workflows = configuration.workflows || {};
  const workflowStatuses = new Map((workflows.checks || []).map((item) => [item.file, item.status]));
  renderConfigGroup(container, "GitHub Actions", (workflows.files || []).map((file) => ({ file, status: workflowStatuses.get(file) || workflows.structural_status || "found" })), "No workflow files found under .github/workflows/.");
  const python = configuration.python_test_configuration || {};
  const validity = python.validity || {};
  renderConfigGroup(container, "Python test configuration", (python.files || []).map((file) => ({ file, status: validity[file] || "found" })), "No recognized pytest configuration files reported.");
  const manifests = configuration.dependency_manifests || {};
  const manifestStatus = manifests.syntax_status || {};
  renderConfigGroup(container, "Dependency manifests", (manifests.files || []).map((file) => ({ file, status: manifestStatus[file] || "found" })), "No recognized dependency manifests reported.");
  const resolution = manifests.dependency_resolution;
  container.append(element("p", "config-limitation", `Dependency resolution: ${statusText(resolution)}. Repository dependencies are not installed by RepoCheck.`));
}

function renderLogs(data) {
  const blocks = [];
  if (data.stdout) blocks.push(`STDOUT\n${data.stdout}`);
  if (data.stderr) blocks.push(`STDERR\n${data.stderr}`);
  const output = blocks.join("\n\n") || "No test output was returned.";
  document.querySelector("#test-logs").textContent = output;
  document.querySelector("#terminal-meta").textContent = `exit ${data.exit_code ?? "not returned"} / ${Number.isFinite(data.duration_seconds) ? `${data.duration_seconds.toFixed(2)} s` : "duration not reported"}`;
  document.querySelector('[data-copy="logs"]').hidden = !blocks.length;
}

function summaryText(data) {
  const rows = [
    `RepoCheck report: ${data.repository || latestUrl}`,
    `Validation: ${statusText(data.validation_status)}`,
    `Tests: ${statusText(data.test_status)}`,
    `Readiness: ${statusText(data.readiness_assessment)}`,
    `Configuration: ${statusText(data.configuration_status)}`,
    `Detected test files (${data.test_file_count ?? "not reported"}): ${(data.test_files || []).join(", ") || "none reported"}`,
  ];
  (data.findings || []).forEach((finding) => rows.push(`- [${finding.severity || "info"}] ${finding.title || finding.code}: ${finding.message || ""}${finding.recommendation ? ` Next: ${finding.recommendation}` : ""}`));
  return rows.join("\n");
}

async function copyText(value, label) {
  try {
    await navigator.clipboard.writeText(value);
    copyFeedback.textContent = `${label} copied.`;
  } catch {
    copyFeedback.textContent = `Clipboard unavailable. Select the ${label.toLowerCase()} in the report and copy it manually.`;
  }
  clearTimeout(feedbackTimer);
  feedbackTimer = setTimeout(() => { copyFeedback.textContent = ""; }, 2500);
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button || !latestReport) return;
  if (button.dataset.copy === "logs") {
    const logs = [latestReport.stdout && `STDOUT\n${latestReport.stdout}`, latestReport.stderr && `STDERR\n${latestReport.stderr}`].filter(Boolean).join("\n\n");
    if (logs) copyText(logs, "Logs");
  }
});

document.querySelector("#copy-summary").addEventListener("click", () => {
  if (latestReport) copyText(summaryText(latestReport), "Summary");
});
document.querySelector("#copy-report").addEventListener("click", () => {
  if (latestReport) copyText(JSON.stringify(latestReport, null, 2), "Report JSON");
});

showScene("intro-screen");
