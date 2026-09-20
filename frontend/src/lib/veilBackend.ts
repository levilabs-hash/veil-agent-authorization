/**
 * Server-only origin of the VEIL FastAPI app.
 * Do not import this module from client components.
 */
export function resolveVeilApiOrigin(request: Request): string {
  const configured = process.env.VEIL_BACKEND_URL?.trim().replace(/\/$/, "");
  if (configured) {
    return configured;
  }
  if (process.env.VERCEL) {
    const host =
      request.headers.get("x-forwarded-host") ||
      request.headers.get("host") ||
      process.env.VERCEL_PROJECT_PRODUCTION_URL ||
      process.env.VERCEL_URL ||
      "";
    if (!host) {
      return "http://127.0.0.1:8000";
    }
    const proto = request.headers.get("x-forwarded-proto") || "https";
    const origin = host.startsWith("http")
      ? host.replace(/\/$/, "")
      : `${proto}://${host.replace(/\/$/, "")}`;
    return `${origin}/veil-api`;
  }
  return "http://127.0.0.1:8000";
}

export function reviewResolveUrl(request: Request, reviewId: string): string {
  const base = resolveVeilApiOrigin(request);
  return `${base}/user/reviews/${encodeURIComponent(reviewId)}/resolve`;
}
