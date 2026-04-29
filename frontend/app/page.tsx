import { revalidatePath } from "next/cache";
import Link from "next/link";
import { EventCluster, RefreshRun, fetchJson, formatDateTime, postJson } from "../lib/api";

export const dynamic = "force-dynamic";

type RadarSearchParams = {
  hours?: string;
  sourceType?: string;
  minScore?: string;
  sort?: string;
};

async function refreshRadarAction() {
  "use server";
  await postJson<RefreshRun>("/api/clusters/refresh");
  revalidatePath("/");
  revalidatePath("/sources");
  revalidatePath("/runs");
}

async function scoreClustersAction() {
  "use server";
  await postJson<{ clustersScored: number }>("/api/clusters/score");
  revalidatePath("/");
}

async function translateClustersAction() {
  "use server";
  await postJson<{
    clustersTranslated: number;
    clustersSkipped: number;
    aiRunsCreated: number;
    errors: string[];
    status: string;
  }>("/api/clusters/translate");
  revalidatePath("/");
}

export default async function RadarPage({
  searchParams,
}: {
  searchParams?: Promise<RadarSearchParams>;
}) {
  const params = (await searchParams) ?? {};
  const query = new URLSearchParams();
  if (params.hours) {
    query.set("hours", params.hours);
  }
  if (params.sourceType) {
    query.set("sourceType", params.sourceType);
  }
  if (params.minScore) {
    query.set("minScore", params.minScore);
  }
  query.set("sort", params.sort || "score");

  let clusters: EventCluster[] = [];
  let error: string | null = null;
  try {
    clusters = await fetchJson<EventCluster[]>(`/api/clusters?${query.toString()}`);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取事件";
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Researcher Intelligence Radar</p>
        <h1>情报雷达</h1>
        <p>按热度、时间、来源和类型扫描已聚类事件，保留每条推荐理由和来源证据。</p>
      </header>

      <div className="toolbar">
        <form className="filterBar" action="/" method="get">
          <label>
            时间
            <select name="hours" defaultValue={params.hours ?? ""}>
              <option value="">全部</option>
              <option value="6">6 小时</option>
              <option value="24">24 小时</option>
              <option value="72">3 天</option>
              <option value="168">7 天</option>
            </select>
          </label>
          <label>
            类型
            <select name="sourceType" defaultValue={params.sourceType ?? ""}>
              <option value="">全部</option>
              <option value="rss">RSS</option>
              <option value="webpage">网页</option>
              <option value="hacker_news">Hacker News</option>
              <option value="github_repo">GitHub repo</option>
              <option value="github_release">GitHub release</option>
              <option value="reddit_subreddit">Reddit subreddit</option>
              <option value="bluesky_search">Bluesky search</option>
              <option value="bluesky_actor_feed">Bluesky author feed</option>
              <option value="mastodon_timeline">Mastodon timeline</option>
            </select>
          </label>
          <label>
            最低分
            <input name="minScore" min="0" max="100" type="number" defaultValue={params.minScore ?? ""} />
          </label>
          <label>
            排序
            <select name="sort" defaultValue={params.sort ?? "score"}>
              <option value="score">热度</option>
              <option value="time">时间</option>
            </select>
          </label>
          <button type="submit">筛选</button>
        </form>
        <form action={refreshRadarAction}>
          <button type="submit">
            刷新情报
          </button>
        </form>
        <form action={scoreClustersAction}>
          <button className="secondaryButton" type="submit">
            重新评分
          </button>
        </form>
        <form action={translateClustersAction}>
          <button className="secondaryButton" type="submit">
            翻译中文
          </button>
        </form>
      </div>

      {error ? <StatePanel title="无法读取事件" detail={error} /> : null}

      {!error && clusters.length === 0 ? (
        <StatePanel title="暂无事件" detail="完成信源抓取、AI 聚类与评分后，事件会出现在这里。" />
      ) : null}

      {!error && clusters.length > 0 ? (
        <div className="timeline">
          {clusters.map((item) => (
            <article className="eventCard" key={item.id}>
              <div className="eventTime">{formatDateTime(item.lastSeenAt)}</div>
              <div className="eventBody">
                <div className="eventMeta">{formatPrimarySource(item)}</div>
                <div className="eventTitleRow">
                  <h2>
                    <Link href={`/events/${item.id}`}>{item.displayTitle}</Link>
                  </h2>
                  <span className="scoreBadge">{item.hotScore}</span>
                </div>
                <p>{item.displaySummary || "暂无摘要"}</p>
                <div className="tagRow">
                  {item.editorialTagsJson.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                  {item.editorialCategory ? <span>{formatEditorialCategory(item.editorialCategory)}</span> : null}
                </div>
                {item.otherSourceTypeCount > 0 ? (
                  <Link className="sourceFoldLink" href={`/events/${item.id}`}>
                    另有 {item.otherSourceTypeCount} 个平台也报道了此事件
                  </Link>
                ) : null}
                <div className="reasonBar">
                  <strong>推荐理由：</strong>
                  <span>{primaryReason(item)}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

const sourceTypeLabels: Record<string, string> = {
  rss: "RSS",
  webpage: "网页",
  hacker_news: "Hacker News",
  github_repo: "GitHub repo",
  github_release: "GitHub release",
  reddit_subreddit: "Reddit",
  bluesky_search: "Bluesky search",
  bluesky_actor_feed: "Bluesky author feed",
  mastodon_timeline: "Mastodon",
};

const editorialCategoryLabels: Record<string, string> = {
  ai_big_news: "AI 大新闻",
  commercial_value: "商业价值",
  watchlist_update: "重点源更新",
  tech_project: "技术项目",
  other: "其他",
};

function formatPrimarySource(item: EventCluster): string {
  if (!item.primarySourceName) {
    return "未记录来源";
  }
  if (!item.primarySourceType) {
    return item.primarySourceName;
  }
  return `${item.primarySourceName}（${sourceTypeLabels[item.primarySourceType] ?? item.primarySourceType}）`;
}

function formatEditorialCategory(category: string): string {
  return editorialCategoryLabels[category] ?? category;
}

function primaryReason(item: EventCluster): string {
  const [reason] = [...item.scoreReasonJson].sort((left, right) => right.score - left.score);
  return reason?.detail || "暂无推荐理由";
}

function StatePanel({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="statePanel">
      <h2>{title}</h2>
      <p>{detail}</p>
    </div>
  );
}
