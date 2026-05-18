import { TimelinePage, fetchJson } from "../../lib/api";
import { getRequestOrigin } from "../../lib/request-origin";
import { renderTimelineRss } from "../../lib/rss";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const feed = await fetchJson<TimelinePage>("/api/public/items?mode=selected&take=50");
  const origin = getRequestOrigin(request);
  const xml = renderTimelineRss("AI HOT - 精选", origin, "AI HOT 精选事件", feed);
  return new Response(xml, {
    headers: { "Content-Type": "application/rss+xml; charset=utf-8" },
  });
}
