import { FeedPage, FeedSearchParams } from "../components/aihot-feed";
import { TimelinePage, fetchJson } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams?: Promise<FeedSearchParams>;
}) {
  const params = (await searchParams) ?? {};
  const query = new URLSearchParams();
  query.set("mode", "selected");
  query.set("page", params.page || "1");
  query.set("take", "40");
  const since = sinceFromHours(params.hours);
  if (since) {
    query.set("since", since);
  }
  if (params.industry) {
    query.set("industry", params.industry);
  }
  if (params.q) {
    query.set("q", params.q);
  }
  const feed = await fetchJson<TimelinePage>(`/api/public/items?${query.toString()}`);

  return (
    <FeedPage
      basePath="/"
      feed={feed}
      params={params}
      showIndustryFilter
      showTimeFilter
      subtitle="AI 自动挑选的高价值内容"
      title="精选"
    />
  );
}

function sinceFromHours(value?: string): string | null {
  const hours = Number(value);
  if (!Number.isFinite(hours) || hours <= 0 || hours > 168) {
    return null;
  }
  return new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
}
