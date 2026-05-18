import { revalidatePath } from "next/cache";
import { SourcePlatformCapability, fetchJson, postJsonBody } from "../../lib/api";

export const dynamic = "force-dynamic";

async function addManualLinkAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/items/manual", {
    title: stringValue(formData, "title"),
    sourceUrl: optionalStringValue(formData, "sourceUrl"),
    contentText: optionalStringValue(formData, "contentText"),
    author: optionalStringValue(formData, "author"),
    sourceName: stringValue(formData, "sourceName", "Manual Link"),
  });
  revalidatePath("/");
  revalidatePath("/source-market");
  revalidatePath("/sources");
}

export default async function SourceMarketPage() {
  let capabilities: SourcePlatformCapability[] = [];
  let error: string | null = null;

  try {
    capabilities = await fetchJson<SourcePlatformCapability[]>("/api/source-market");
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取信源市场";
  }

  const available = capabilities.filter((item) => item.status === "available");
  const manual = capabilities.filter((item) => item.automationLevel === "manual");
  const deferred = capabilities.filter((item) => item.status !== "available" && item.automationLevel !== "manual");

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Source Market</p>
        <h1>信源市场</h1>
        <p>按平台能力分级管理自动化、授权、补录和暂缓接入边界。</p>
      </header>

      {error ? <StatePanel title="无法读取信源市场" detail={error} /> : null}

      {!error ? (
        <>
          <div className="panelGrid">
            <CapabilityPanel items={available} title="可自动化" />
            <CapabilityPanel items={manual} title="人工补录" />
          </div>

          <section className="panel">
            <div className="sourcePanelHeader">
              <div>
                <p className="eyebrow">Manual Evidence</p>
                <h2>链接补录</h2>
              </div>
              <span className="statusBadge">RawItem</span>
            </div>
            <form action={addManualLinkAction} className="sourceForm">
              <div className="sourceFormGrid">
                <label className="fieldStack">
                  标题
                  <input name="title" placeholder="事件或文章标题" required />
                </label>
                <label className="fieldStack">
                  来源名称
                  <input defaultValue="Manual Link" name="sourceName" required />
                </label>
                <label className="fieldStack">
                  链接
                  <input name="sourceUrl" placeholder="https://example.com/article" type="url" />
                </label>
                <label className="fieldStack">
                  作者
                  <input name="author" placeholder="可选" />
                </label>
              </div>
              <label className="fieldStack">
                摘要或引用片段
                <textarea name="contentText" placeholder="公开内容摘录、人工备注或关键证据片段" />
              </label>
              <button type="submit">补录链接</button>
            </form>
          </section>

          <CapabilityPanel items={deferred} title="后续接入" wide />
        </>
      ) : null}
    </section>
  );
}

function CapabilityPanel({
  items,
  title,
  wide,
}: {
  items: SourcePlatformCapability[];
  title: string;
  wide?: boolean;
}) {
  return (
    <section className={wide ? "panel" : "panel"}>
      <div className="sourcePanelHeader">
        <div>
          <p className="eyebrow">{title}</p>
          <h2>{title}</h2>
        </div>
        <span className="statusBadge">{items.length}</span>
      </div>
      <div className="logTable">
        {items.map((item) => (
          <div className="logRow" key={`${item.platform}-${item.sourceType}`}>
            <strong>{item.platform}</strong>
            <span>{item.automationLevel}</span>
            <small>
              {item.accessMode} / {item.costLevel} / {item.requiresApproval ? "需审核" : "免审核"} /{" "}
              {item.notes}
            </small>
          </div>
        ))}
      </div>
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

function stringValue(formData: FormData, key: string, fallback = ""): string {
  const value = formData.get(key);
  if (typeof value !== "string" || !value.trim()) {
    return fallback;
  }
  return value.trim();
}

function optionalStringValue(formData: FormData, key: string): string | null {
  const value = stringValue(formData, key);
  return value || null;
}
