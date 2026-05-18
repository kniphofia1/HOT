import { FeedPage, FeedSearchParams } from "../../components/aihot-feed";
import { TimelinePage, fetchJson } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function AllPage({
  searchParams,
}: {
  searchParams?: Promise<FeedSearchParams>;
}) {
  const params = (await searchParams) ?? {};
  const query = new URLSearchParams();
  query.set("mode", "all");
  query.set("page", params.page || "1");
  query.set("take", "40");
  const since = sinceFromHours(params.hours);
  if (since) {
    query.set("since", since);
  }
  if (params.industry) {
    query.set("industry", params.industry);
  }
  if (params.sourceKind) {
    query.set("sourceKind", params.sourceKind);
  }
  if (params.q) {
    query.set("q", params.q);
  }
  const feed = await fetchJson<TimelinePage>(`/api/public/items?${query.toString()}`);

  return (
    <FeedPage
      basePath="/all"
      feed={feed}
      params={params}
      showIndustryFilter
      showSourceFilter
      showTimeFilter
      subtitle="完整事件流，按时间、信源和行业持续滚动"
      title="全部动态"
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
