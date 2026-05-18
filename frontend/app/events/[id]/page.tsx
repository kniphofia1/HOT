import { notFound } from "next/navigation";
import { EventClusterDetail, fetchJson, formatDateTime } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function EventDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let event: EventClusterDetail;
  try {
    event = await fetchJson<EventClusterDetail>(`/api/clusters/${id}`);
  } catch {
    notFound();
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">{formatDateTime(event.lastSeenAt)}</p>
        <h1>{event.displayTitle}</h1>
        <p>{event.displaySummary || "暂无摘要"}</p>
      </header>

      <div className="metricStrip">
        <div>
          <span>热度</span>
          <strong>{event.hotScore}</strong>
        </div>
        <div>
          <span>阶段</span>
          <strong>{formatEventPhase(event.eventPhase)}</strong>
        </div>
        <div>
          <span>传播</span>
          <strong>{event.propagationScore}</strong>
        </div>
        <div>
          <span>置信度</span>
          <strong>{event.confidence}</strong>
        </div>
        <div>
          <span>可信度</span>
          <strong>{event.credibilityScore}</strong>
        </div>
        <div>
          <span>证据</span>
          <strong>{event.evidenceCount}</strong>
        </div>
      </div>

      <section className="panel">
        <h2>事件状态</h2>
        <div className="reasonGrid">
          <div className="reasonPill">
            <strong>主信源</strong>
            <span>{event.primarySourceName || "未识别"}</span>
            <small>{event.primarySourceType || "暂无类型"}</small>
          </div>
          <div className="reasonPill">
            <strong>覆盖平台</strong>
            <span>{event.sourceTypes.length}</span>
            <small>{event.sourceTypes.join(" / ") || "暂无来源类型"}</small>
          </div>
          <div className="reasonPill">
            <strong>首次发现</strong>
            <span>{formatDateTime(event.firstSeenAt)}</span>
            <small>最近更新 {formatDateTime(event.lastSeenAt)}</small>
          </div>
        </div>
        {event.editorialTagsJson.length > 0 ? (
          <div className="tagRow">
            {event.editorialTagsJson.map((tag) => (
              <span key={tag}>{tag}</span>
            ))}
          </div>
        ) : null}
      </section>

      <section className="panel">
        <h2>智能判断</h2>
        <div className="reasonGrid">
          {event.intelligenceReasonJson.map((reason) => (
            <div className="reasonPill" key={reason.key}>
              <strong>{reason.label}</strong>
              <span>{reason.score}</span>
              <small>{reason.detail}</small>
            </div>
          ))}
        </div>
        <div className="tagRow">
          {event.impactDomainsJson.map((domain) => (
            <span key={domain}>{formatImpactDomain(domain)}</span>
          ))}
          {event.entitiesJson.map((entity) => (
            <span key={entity}>{entity}</span>
          ))}
        </div>
      </section>

      {event.historicalMatchesJson.length > 0 ? (
        <section className="panel">
          <h2>相似历史事件</h2>
          <div className="logTable">
            {event.historicalMatchesJson.map((match) => (
              <div className="logRow" key={match.clusterId}>
                <strong>{match.score}</strong>
                <span>{formatDateTime(match.lastSeenAt)}</span>
                <small>{match.title}</small>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="panel">
        <h2>推荐理由</h2>
        <div className="reasonGrid">
          {event.scoreReasonJson.map((reason) => (
            <div className="reasonPill" key={reason.key}>
              <strong>{reason.label}</strong>
              <span>{reason.score}</span>
              <small>{reason.detail}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>来源引用</h2>
        <div className="evidenceList">
          {event.evidence.map((item) => (
            <article className="evidenceItem" key={item.id}>
              <div className="eventMeta">
                {item.sourceName} / 来源发布时间 {formatDateTime(item.rawPublishedAt)}
              </div>
              <h3>{item.rawTitle}</h3>
              <p>{item.quote || item.rawContentText || "暂无引用片段"}</p>
              <a href={item.sourceUrl} rel="noreferrer" target="_blank">
                打开来源
              </a>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

const eventPhaseLabels: Record<string, string> = {
  unknown: "未知",
  emerging: "刚出现",
  spreading: "扩散中",
  peaking: "峰值期",
  tracking: "跟踪中",
  decaying: "衰退中",
};

const impactDomainLabels: Record<string, string> = {
  ai_tech: "AI/技术",
  developer_platform: "开发者平台",
  product_business: "产品/商业",
  capital_market: "资本市场",
  policy_risk: "政策/风险",
  social_signal: "社交信号",
};

function formatEventPhase(phase: string | null): string {
  return phase ? eventPhaseLabels[phase] ?? phase : "未知";
}

function formatImpactDomain(domain: string): string {
  return impactDomainLabels[domain] ?? domain;
}
