import type { ValidationReport } from "../types";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function responseError(body: unknown, status: number): string {
  const detail = typeof body === "object" && body !== null && "detail" in body
    ? (body as { detail?: unknown }).detail
    : undefined;
  if (typeof detail === "string") return `HTTP ${status}: ${detail}`;
  if (Array.isArray(detail)) {
    return `HTTP ${status}: ${detail.map((item) => typeof item === "object" && item && "msg" in item ? String(item.msg) : "Invalid request").join("; ")}`;
  }
  if (status === 429) return "GitHub rate limited the inspection request. Wait briefly and retry.";
  return `RepoCheck returned HTTP ${status}. The repository has not been assessed.`;
}

export async function validateRepository(url: string, signal?: AbortSignal, runId?: string): Promise<ValidationReport> {
  let response: Response;
  try {
    response = await fetch("/repositories/validate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(runId ? { "X-RepoCheck-Run-ID": runId } : {}),
      },
      body: JSON.stringify({ url }),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    if (error instanceof TypeError) throw new ApiError("RepoCheck's API could not be reached. Check the service connection and retry.");
    throw new ApiError("The request could not be completed.");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(responseError(body, response.status));
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new ApiError("The API response was not a validation report.");
  return body as ValidationReport;
}
