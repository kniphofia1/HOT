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
          <span>置信度</span>
          <strong>{event.confidence}</strong>
        </div>
        <div>
          <span>证据</span>
          <strong>{event.evidenceCount}</strong>
        </div>
      </div>

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
              <div className="eventMeta">{item.sourceName}</div>
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
