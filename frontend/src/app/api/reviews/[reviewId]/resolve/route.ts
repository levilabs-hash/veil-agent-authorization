import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function backendBase(): string {
  return (process.env.VEIL_BACKEND_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    ""
  );
}

export async function POST(
  request: Request,
  context: { params: Promise<{ reviewId: string }> }
) {
  const token = process.env.VEIL_OPERATOR_TOKEN?.trim();
  if (!token) {
    return NextResponse.json(
      { detail: "Operator approval is not configured." },
      { status: 503 }
    );
  }
  const { reviewId } = await context.params;
  let approved = false;
  try {
    const body = (await request.json()) as { approved?: boolean };
    approved = Boolean(body.approved);
  } catch {
    approved = false;
  }
  const response = await fetch(
    `${backendBase()}/user/reviews/${encodeURIComponent(reviewId)}/resolve`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ approved }),
    }
  );
  const payload = await response.json().catch(() => ({
    detail: "VEIL backend did not return JSON.",
  }));
  return NextResponse.json(payload, { status: response.status });
}
