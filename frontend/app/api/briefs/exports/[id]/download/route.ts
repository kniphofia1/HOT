import { NextRequest } from "next/server";

const API_BASE_URL =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await fetch(`${API_BASE_URL}/api/briefs/exports/${encodeURIComponent(id)}/download`, {
    cache: "no-store",
  });
  const headers = new Headers();
  const contentType = response.headers.get("content-type");
  const disposition = response.headers.get("content-disposition");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  if (disposition) {
    headers.set("content-disposition", disposition);
  }
  return new Response(await response.text(), { status: response.status, headers });
}
