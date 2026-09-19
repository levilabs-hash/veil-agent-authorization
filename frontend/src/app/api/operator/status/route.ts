import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const configured = Boolean(process.env.VEIL_OPERATOR_TOKEN?.trim());
  return NextResponse.json({ available: configured });
}
