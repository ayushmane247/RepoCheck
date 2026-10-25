import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { resultState } from "./App";
import type { ValidationReport } from "./types";

const report: ValidationReport = {
  repository: "owner/repo", default_branch: "main", validation_status: "completed", test_status: "passed",
  readiness_assessment: "needs_attention", configuration_status: "issues_found", language: "python", framework: "pytest",
  test_files: ["tests/test_app.py"], test_file_count: 1, exit_code: 0, duration_seconds: 1.24,
  message: "Tests passed with configuration findings.", stdout: "4 passed in 0.10s", stderr: "",
  findings: [
    { code: "TESTS_PASSED", severity: "info", title: "Tests passed", message: "Runner completed." },
    { code: "NO_GITHUB_ACTIONS_WORKFLOWS", severity: "warning", title: "No workflows", file: ".github/workflows" },
  ],
  configuration: { workflows: { files: [] }, python_test_configuration: { files: ["pytest.ini"], validity: { "pytest.ini": "valid" } }, dependency_manifests: { files: ["requirements.txt"], syntax_status: { "requirements.txt": "valid" }, dependency_resolution: "not_attempted" } },
};

function successResponse(value: unknown = report) {
  return { ok: true, status: 200, json: async () => value } as Response;
}

describe("RepoCheck frontend", () => {
  const clipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, "clipboard");
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    if (clipboardDescriptor) Object.defineProperty(navigator, "clipboard", clipboardDescriptor);
    else Reflect.deleteProperty(navigator, "clipboard");
  });
  beforeEach(() => { vi.restoreAllMocks(); });

  it("keeps final result states tied to the API outcome and warnings", () => {
    expect(resultState({ validation_status: "completed", test_status: "passed", readiness_assessment: "checks_passed", findings: [{ severity: "warning" }] })).toBe("warning");
    expect(resultState({ validation_status: "completed", test_status: "passed", readiness_assessment: "checks_passed" })).toBe("success");
    expect(resultState({ validation_status: "completed", test_status: "failed", readiness_assessment: "needs_attention" })).toBe("failure");
    expect(resultState({ validation_status: "completed", test_status: "collection_failed" })).toBe("failure");
    expect(resultState({ validation_status: "completed", test_status: "timed_out" })).toBe("failure");
    expect(resultState({ validation_status: "completed", test_status: "runner_error" })).toBe("failure");
    expect(resultState({ validation_status: "completed", test_status: "no_tests", readiness_assessment: "not_assessed" })).toBe("partial");
    expect(resultState({ validation_status: "failed", test_status: "incomplete" })).toBe("error");
  });

  it("opens the briefing from the cinematic introduction", async () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /every repository/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));
    expect(await screen.findByRole("heading", { name: /drop the coordinates/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/repository coordinates/i)).toHaveFocus();
    expect(document.querySelector(".rooftop-art")).toHaveAttribute("viewBox", "0 0 700 430");
    fireEvent.click(screen.getByRole("link", { name: "RepoCheck home" }));
    expect(await screen.findByRole("heading", { name: /every repository/i })).toBeInTheDocument();
  });

  it("validates the URL, shows honest loading, renders response fields and filters findings", async () => {
    let resolve!: (value: Response) => void;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      if (String(input).startsWith("/repositories/progress/")) {
        return Promise.resolve(successResponse({ stage: "Running detected tests in the restricted Docker runner" }));
      }
      return new Promise((done) => { resolve = done; });
    });
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));
    await screen.findByRole("heading", { name: /drop the coordinates/i });
    fireEvent.change(screen.getByLabelText(/repository coordinates/i), { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
    expect(await screen.findByText(/stays active until the API returns its report/i)).toBeInTheDocument();
    expect(await screen.findByText(/Running detected tests in the restricted Docker runner/)).toBeInTheDocument();
    expect(screen.getByText(/Server-reported stage/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([url]) => url === "/repositories/validate")).toHaveLength(1);
    expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
    resolve(successResponse());
    expect(await screen.findByRole("heading", { name: /this setup needs a closer look/i })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/repositories/validate", expect.objectContaining({ method: "POST", body: JSON.stringify({ url: "https://github.com/owner/repo" }) }));
    expect(screen.getByText("needs attention")).toBeInTheDocument();
    expect(screen.getByText("2", { selector: ".count-chip" })).toBeInTheDocument();
    fireEvent.click(screen.getByText("Tests passed"));
    expect(screen.getByText(/Detected test files: tests\/test_app\.py/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "WARNINGS" }));
    expect(screen.getByText("No workflows")).toBeInTheDocument();
    expect(screen.queryByText("Tests passed")).not.toBeInTheDocument();
    expect(screen.getByText(/Other CI systems and remote settings were not checked/)).toBeInTheDocument();
    expect(screen.getByText("pytest.ini")).toBeInTheDocument();
    expect(screen.getByText(/Repository dependencies are not installed/)).toBeInTheDocument();
  });

  it("uses the configured API base for validation and progress polling", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://example-api.example.com///");
    let resolveValidation!: (value: Response) => void;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      if (String(input).includes("/repositories/progress/")) {
        return Promise.resolve(successResponse({ stage: "Live progress from the configured API." }));
      }
      return new Promise((resolve) => { resolveValidation = resolve; });
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));
    await screen.findByRole("heading", { name: /drop the coordinates/i });
    fireEvent.change(screen.getByLabelText(/repository coordinates/i), { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
    expect(await screen.findByText("Live progress from the configured API.")).toBeInTheDocument();

    const progressCall = fetchMock.mock.calls.find(([input]) => String(input).includes("/repositories/progress/"));
    expect(progressCall).toBeDefined();
    const progressUrl = String(progressCall?.[0]);
    expect(progressUrl).toMatch(/^https:\/\/example-api\.example\.com\/repositories\/progress\//);
    const runId = progressUrl.split("/").at(-1);

    resolveValidation(successResponse());
    await screen.findByRole("heading", { name: /this setup needs a closer look/i });

    const validationCall = fetchMock.mock.calls.find(([input]) => String(input).endsWith("/repositories/validate"));
    expect(validationCall?.[0]).toBe("https://example-api.example.com/repositories/validate");
    expect((validationCall?.[1]?.headers as Record<string, string>)["X-RepoCheck-Run-ID"]).toBe(runId);
  });

  it("shows findings in severity order and omits metadata the API did not return", async () => {
    const mixedReport: ValidationReport = {
      validation_status: "completed", test_status: "failed", readiness_assessment: "needs_attention",
      findings: [
        { severity: "info", title: "Informational" },
        { severity: "warning", title: "Warning" },
        { severity: "error", title: "Error" },
      ],
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(successResponse(mixedReport));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));
    await screen.findByRole("heading", { name: /drop the coordinates/i });
    fireEvent.change(screen.getByLabelText(/repository coordinates/i), { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
    await screen.findByRole("heading", { name: /tests need your attention/i });
    const titles = [...document.querySelectorAll(".finding-heading strong")].map((element) => element.textContent);
    expect(titles).toEqual(["Error", "Warning", "Informational"]);
    expect(screen.queryByText("not reported")).not.toBeInTheDocument();
    expect(screen.queryByText("GitHub Actions")).not.toBeInTheDocument();
  });

  it("rejects non-GitHub inputs without submitting", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));
    await screen.findByRole("heading", { name: /drop the coordinates/i });
    fireEvent.change(screen.getByLabelText(/repository coordinates/i), { target: { value: "https://example.com/user/repo" } });
    fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
    expect(screen.getByRole("alert")).toHaveTextContent("valid HTTPS GitHub repository URL");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps a network failure unjudged and supports retry and new analysis", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("offline")).mockResolvedValueOnce(successResponse());
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));
    await screen.findByRole("heading", { name: /drop the coordinates/i });
    fireEvent.change(screen.getByLabelText(/repository coordinates/i), { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
    expect(await screen.findByRole("heading", { name: /repository remains unjudged/i })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("could not be reached");
    fireEvent.click(screen.getByRole("button", { name: /retry analysis/i }));
    await waitFor(() => expect(screen.getByRole("heading", { name: /this setup needs a closer look/i })).toBeInTheDocument());
    fireEvent.click(screen.getAllByRole("button", { name: /new analysis/i })[0]);
    await waitFor(() => expect(screen.getByRole("heading", { name: /drop the coordinates/i })).toBeInTheDocument());
  });

  it("copies the actual API report and announces the result", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(successResponse());
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /get started/i }));
    await screen.findByRole("heading", { name: /drop the coordinates/i });
    fireEvent.change(screen.getByLabelText(/repository coordinates/i), { target: { value: "https://github.com/owner/repo" } });
    fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
    await screen.findByRole("heading", { name: /this setup needs a closer look/i });
    fireEvent.click(screen.getByRole("button", { name: /copy report/i }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(JSON.stringify(report, null, 2)));
    expect(await screen.findByText("Copied to clipboard.")).toBeInTheDocument();
  });
});
