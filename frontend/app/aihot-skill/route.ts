import { getRequestOrigin } from "../../lib/request-origin";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return Response.redirect(new URL("/aihot-skill/SKILL.md", getRequestOrigin(request)), 302);
}
