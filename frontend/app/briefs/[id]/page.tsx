import { revalidatePath } from "next/cache";
import { notFound } from "next/navigation";
import {
  BriefDelivery,
  BriefExport,
  fetchJson,
  formatDateTime,
  postJsonBody,
  PUBLIC_API_BASE_URL,
} from "../../../lib/api";

export const dynamic = "force-dynamic";

async function createDeliveryAction(formData: FormData) {
  "use server";
  const exportId = String(formData.get("exportId") || "");
  await postJsonBody<BriefDelivery>(`/api/briefs/exports/${exportId}/deliveries`, {
    targetType: String(formData.get("targetType") || "local_archive"),
    targetLabel: String(formData.get("targetLabel") || ""),
  });
  revalidatePath(`/briefs/${exportId}`);
}

export default async function BriefDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let brief: BriefExport;
  let deliveries: BriefDelivery[] = [];
  try {
    [brief, deliveries] = await Promise.all([
      fetchJson<BriefExport>(`/api/briefs/exports/${id}`),
      fetchJson<BriefDelivery[]>(`/api/briefs/exports/${id}/deliveries`),
    ]);
  } catch {
    notFound();
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">{formatDateTime(brief.generatedAt)}</p>
        <h1>{brief.title}</h1>
        <p>{brief.eventClusterIdsJson.length} 个事件已写入交付简报，支持 Markdown、Word 和打印 HTML。</p>
      </header>

      <div className="toolbar">
        <a className="buttonLink" href={`${PUBLIC_API_BASE_URL}/api/briefs/exports/${brief.id}/download`}>
          下载 Markdown
        </a>
        <a className="buttonLink" href={`${PUBLIC_API_BASE_URL}/api/briefs/exports/${brief.id}/download/docx`}>
          下载 Word
        </a>
        <a className="buttonLink" href={`${PUBLIC_API_BASE_URL}/api/briefs/exports/${brief.id}/download/html`}>
          打印 HTML
        </a>
        <a className="buttonLink secondary" href="/briefs">
          重新生成
        </a>
      </div>

      <section className="panel">
        <div className="sourcePanelHeader">
          <div>
            <p className="eyebrow">Delivery Center</p>
            <h2>交付目标</h2>
          </div>
          <span className="statusBadge">{deliveries.length}</span>
        </div>
        <form action={createDeliveryAction} className="sourceForm">
          <input name="exportId" type="hidden" value={brief.id} />
          <div className="sourceFormGrid">
            <label className="fieldStack">
              渠道
              <select name="targetType" defaultValue="local_archive">
                <option value="local_archive">本地归档</option>
                <option value="email">邮件</option>
                <option value="feishu">飞书</option>
                <option value="notion">Notion</option>
                <option value="slack">Slack</option>
              </select>
            </label>
            <label className="fieldStack">
              目标名称
              <input name="targetLabel" placeholder="客户、频道、空间或归档名" />
            </label>
          </div>
          <button type="submit">创建交付计划</button>
        </form>
        {deliveries.length > 0 ? (
          <div className="logTable">
            {deliveries.map((delivery) => (
              <div className="logRow" key={delivery.id}>
                <strong>{delivery.targetType}</strong>
                <span>{delivery.status}</span>
                <small>
                  {delivery.targetLabel} / {delivery.errorMessage || "可本地交付"}
                </small>
              </div>
            ))}
          </div>
        ) : (
          <p>暂无交付计划。</p>
        )}
      </section>

      <section className="panel">
        <h2>Markdown 预览</h2>
        <pre className="markdownPreview">{brief.markdown}</pre>
      </section>
    </section>
  );
}
