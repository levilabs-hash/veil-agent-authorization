import type { AuditEvent, DemoRun } from "./types";

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

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new BackendUnavailableError(
      `VEIL backend returned HTTP ${response.status}`
    );
  }
  return (await response.json()) as T;
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
