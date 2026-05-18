import { redirect } from "next/navigation";
import {
  BriefExport,
  BriefTemplate,
  EventCluster,
  fetchJson,
  formatDateTime,
  postJsonBody,
} from "../../lib/api";

export const dynamic = "force-dynamic";

async function createBriefAction(formData: FormData) {
  "use server";
  const eventClusterIds = formData.getAll("eventClusterIds").map(String).filter(Boolean);
  const manualNotes: Record<string, string> = {};
  for (const id of eventClusterIds) {
    const note = String(formData.get(`manualNote:${id}`) || "").trim();
    if (note) {
      manualNotes[id] = note;
    }
  }

  const created = await postJsonBody<BriefExport>("/api/briefs/exports", {
    templateId: String(formData.get("templateId") || ""),
    title: String(formData.get("title") || "研究员情报简报"),
    eventClusterIds,
    manualNotes,
  });
  redirect(`/briefs/${created.id}`);
}

export default async function BriefsPage() {
  let templates: BriefTemplate[] = [];
  let clusters: EventCluster[] = [];
  let exports: BriefExport[] = [];
  let error: string | null = null;

  try {
    [templates, clusters, exports] = await Promise.all([
      fetchJson<BriefTemplate[]>("/api/briefs/templates"),
      fetchJson<EventCluster[]>("/api/clusters?sort=score"),
      fetchJson<BriefExport[]>("/api/briefs/exports"),
    ]);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取简报数据";
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Briefs</p>
        <h1>商业简报</h1>
        <p>勾选事件、选择模板、补充人工点评，然后生成可下载、可归档、可交付的情报简报。</p>
      </header>

      {error ? <StatePanel title="无法读取简报数据" detail={error} /> : null}

      {!error ? (
        <div className="briefLayout">
          <form className="panel briefForm" action={createBriefAction}>
            <h2>生成简报</h2>
            <label>
              标题
              <input name="title" defaultValue="研究员情报简报" />
            </label>
            <label>
              模板
              <select name="templateId" defaultValue={templates[0]?.id ?? ""}>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>

            {clusters.length === 0 ? (
              <StatePanel title="暂无可选事件" detail="完成聚类和评分后，可以在这里勾选事件生成简报。" />
            ) : (
              <div className="briefEventList">
                {clusters.map((cluster) => (
                  <article className="briefEventItem" key={cluster.id}>
                    <label className="checkboxLine">
                      <input name="eventClusterIds" type="checkbox" value={cluster.id} />
                      <span>{cluster.displayTitle}</span>
                    </label>
                    <div className="eventMeta">
                      热度 {cluster.hotScore} / Evidence {cluster.evidenceCount} / {formatDateTime(cluster.lastSeenAt)}
                    </div>
                    <textarea
                      name={`manualNote:${cluster.id}`}
                      placeholder="人工点评，可留空"
                      rows={3}
                    />
                  </article>
                ))}
              </div>
            )}

            <button type="submit">生成交付简报</button>
          </form>

          <section className="panel">
            <h2>历史导出</h2>
            {exports.length === 0 ? (
              <p>暂无导出记录。</p>
            ) : (
              <div className="exportList">
                {exports.map((item) => (
                  <a className="exportLink" href={`/briefs/${item.id}`} key={item.id}>
                    <strong>{item.title}</strong>
                    <span>{formatDateTime(item.generatedAt)} / {item.exportFormatsJson.join(" / ") || "markdown"}</span>
                  </a>
                ))}
              </div>
            )}
          </section>
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
