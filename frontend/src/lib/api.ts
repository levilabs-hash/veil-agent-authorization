import type { AuditEvent, DemoRun, ReviewResolution } from "./types";

function resolveApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_VEIL_API_BASE?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  if (process.env.NODE_ENV === "production") {
    return "/veil-api";
  }
  return "http://localhost:8000";
}

export const VEIL_API_BASE = resolveApiBase();

export class BackendUnavailableError extends Error {
  constructor(message = "VEIL backend is unavailable") {
    super(message);
    this.name = "BackendUnavailableError";
  }
}

export class OperatorApprovalError extends Error {
  constructor(message = "Operator approval is unavailable") {
    super(message);
    this.name = "OperatorApprovalError";
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : "";
    if (response.status === 401 || response.status === 503) {
      throw new OperatorApprovalError(
        detail || "Operator approval is unavailable."
      );
    }
    throw new BackendUnavailableError(
      `VEIL backend returned HTTP ${response.status}`
    );
  }
  return body as T;
}

export async function fetchHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${VEIL_API_BASE}/health`, {
      cache: "no-store",
    });
    if (!response.ok) return false;
    const body = (await response.json()) as { status?: string };
    return body.status === "ok";
  } catch {
    return false;
  }
}

export async function fetchEvents(): Promise<AuditEvent[]> {
  const response = await fetch(`${VEIL_API_BASE}/events`, { cache: "no-store" });
  return parseJson<AuditEvent[]>(response);
}

export async function runDemo(scenario: string): Promise<DemoRun> {
  let response: Response;
  try {
    response = await fetch(`${VEIL_API_BASE}/demo/${scenario}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    throw new BackendUnavailableError(
      "Cannot reach the VEIL backend. Start it with uvicorn on port 8000."
    );
  }
  return parseJson<DemoRun>(response);
}

export async function fetchOperatorStatus(): Promise<boolean> {
  try {
    const response = await fetch("/api/operator/status", { cache: "no-store" });
    if (!response.ok) return false;
    const body = (await response.json()) as { available?: boolean };
    return body.available === true;
  } catch {
    return false;
  }
}

export async function resolveReview(
  reviewId: string,
  approved: boolean
): Promise<ReviewResolution> {
  let response: Response;
  try {
    response = await fetch(
      `/api/reviews/${encodeURIComponent(reviewId)}/resolve`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      }
    );
  } catch {
    throw new OperatorApprovalError(
      "Cannot reach the operator approval path. The tool was not executed."
    );
  }
  return parseJson<ReviewResolution>(response);
}
