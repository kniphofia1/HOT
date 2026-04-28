import { notFound } from "next/navigation";
import { BriefExport, fetchJson, formatDateTime, PUBLIC_API_BASE_URL } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function BriefDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let brief: BriefExport;
  try {
    brief = await fetchJson<BriefExport>(`/api/briefs/exports/${id}`);
  } catch {
    notFound();
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">{formatDateTime(brief.generatedAt)}</p>
        <h1>{brief.title}</h1>
        <p>{brief.eventClusterIdsJson.length} 个事件已写入 Markdown 简报。</p>
      </header>

      <div className="toolbar">
        <a className="buttonLink" href={`${PUBLIC_API_BASE_URL}/api/briefs/exports/${brief.id}/download`}>
          下载 Markdown
        </a>
        <a className="buttonLink secondary" href="/briefs">
          重新生成
        </a>
      </div>

      <section className="panel">
        <h2>Markdown 预览</h2>
        <pre className="markdownPreview">{brief.markdown}</pre>
      </section>
    </section>
  );
}
