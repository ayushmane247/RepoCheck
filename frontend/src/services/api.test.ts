import { afterEach, describe, expect, it, vi } from "vitest";
import { apiUrl, validateRepository } from "./api";

describe("API URL construction", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("keeps API paths relative when the base URL is unset or empty", () => {
    vi.stubEnv("VITE_API_BASE_URL", undefined);
    expect(apiUrl("/repositories/validate")).toBe("/repositories/validate");

    vi.stubEnv("VITE_API_BASE_URL", "");
    expect(apiUrl("/repositories/progress/run-123")).toBe("/repositories/progress/run-123");
  });

  it("prefixes paths and removes trailing and leading slash duplicates", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://example-api.example.com///");

    expect(apiUrl("/repositories/validate")).toBe("https://example-api.example.com/repositories/validate");
    expect(apiUrl("///repositories/progress/run-123")).toBe("https://example-api.example.com/repositories/progress/run-123");
  });

  it("uses the configured URL for validation while preserving request options", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://example-api.example.com/");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ repository: "owner/repo" }),
    } as Response);
    const controller = new AbortController();

    await validateRepository("https://github.com/owner/repo", controller.signal, "run-123");

    expect(fetchMock).toHaveBeenCalledWith(
      "https://example-api.example.com/repositories/validate",
      expect.objectContaining({
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-RepoCheck-Run-ID": "run-123",
        },
        body: JSON.stringify({ url: "https://github.com/owner/repo" }),
        signal: controller.signal,
      }),
    );
  });
});
