import { revalidatePath } from "next/cache";
import Link from "next/link";
import { EventCluster, fetchJson, formatDateTime, postJson } from "../lib/api";

export const dynamic = "force-dynamic";

type RadarSearchParams = {
  hours?: string;
  sourceType?: string;
  minScore?: string;
  sort?: string;
};

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
                <div className="eventMeta">{item.sourceNames.join(" / ") || "未记录来源"}</div>
                <div className="eventTitleRow">
                  <h2>
                    <Link href={`/events/${item.id}`}>{item.displayTitle}</Link>
                  </h2>
                  <span className="scoreBadge">{item.hotScore}</span>
                </div>
                <p>{item.displaySummary || "暂无摘要"}</p>
                <div className="tagRow">
                  {item.sourceTypes.map((type) => (
                    <span key={type}>{type}</span>
                  ))}
                  <span>{item.evidenceCount} 条 Evidence</span>
                  <span>置信度 {item.confidence}</span>
                </div>
                <div className="reasonGrid">
                  {item.scoreReasonJson.map((reason) => (
                    <div className="reasonPill" key={reason.key}>
                      <strong>{reason.label}</strong>
                      <span>{reason.score}</span>
                      <small>{reason.detail}</small>
                    </div>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function StatePanel({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="statePanel">
      <h2>{title}</h2>
      <p>{detail}</p>
    </div>
  );
}
