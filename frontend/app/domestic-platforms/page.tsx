import { revalidatePath } from "next/cache";
import { DomesticPlatformPolicy, fetchJson, postJsonBody } from "../../lib/api";

export const dynamic = "force-dynamic";

async function addDomesticManualLinkAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/items/manual", {
    title: stringValue(formData, "title"),
    sourceUrl: optionalStringValue(formData, "sourceUrl"),
    contentText: optionalStringValue(formData, "contentText"),
    author: optionalStringValue(formData, "author"),
    platform: stringValue(formData, "platform"),
    sourceName: stringValue(formData, "sourceName", "Manual Domestic"),
  });
  revalidatePath("/");
  revalidatePath("/domestic-platforms");
  revalidatePath("/source-market");
}

export default async function DomesticPlatformsPage() {
  let policies: DomesticPlatformPolicy[] = [];
  let error: string | null = null;

  try {
    policies = await fetchJson<DomesticPlatformPolicy[]>("/api/domestic-platforms");
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取国内平台合规矩阵";
  }

  const official = policies.filter((item) => item.status === "official_auth_required");
  const manual = policies.filter((item) => item.status === "manual_only");

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Domestic Platforms</p>
        <h1>国内平台合规接入</h1>
        <p>微博、B站、知乎、微信公众号、小红书、抖音和快手只走官方授权或人工补录，不做 Cookie、登录态、验证码或私有页面抓取。</p>
      </header>

      {error ? <StatePanel title="无法读取国内平台合规矩阵" detail={error} /> : null}

      {!error ? (
        <>
          <div className="panelGrid">
            <PolicyPanel items={official} title="需官方授权" />
            <PolicyPanel items={manual} title="仅人工补录" />
          </div>

          <section className="panel">
            <div className="sourcePanelHeader">
              <div>
                <p className="eyebrow">Manual Domestic Evidence</p>
                <h2>国内平台链接补录</h2>
              </div>
              <span className="statusBadge">RawItem</span>
            </div>
            <form action={addDomesticManualLinkAction} className="sourceForm">
              <div className="sourceFormGrid">
                <label className="fieldStack">
                  平台
                  <select name="platform" required>
                    {policies.map((policy) => (
                      <option key={policy.platform} value={policy.platform}>
                        {policy.platform}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="fieldStack">
                  信源名称
                  <input defaultValue="Manual Domestic" name="sourceName" required />
                </label>
                <label className="fieldStack">
                  标题
                  <input name="title" placeholder="事件或内容标题" required />
                </label>
                <label className="fieldStack">
                  链接
                  <input name="sourceUrl" placeholder="https://example.com/post" type="url" />
                </label>
                <label className="fieldStack">
                  作者
                  <input name="author" placeholder="可选" />
                </label>
              </div>
              <label className="fieldStack">
                摘要或引用片段
                <textarea name="contentText" placeholder="人工摘录公开内容、背景说明或关键证据片段" />
              </label>
              <button type="submit">补录为证据</button>
            </form>
          </section>

          <section className="panel">
            <div className="sourcePanelHeader">
              <div>
                <p className="eyebrow">Blocked Paths</p>
                <h2>明确禁止</h2>
              </div>
              <span className="statusBadge off">No scraping bypass</span>
            </div>
            <div className="tagRow">
              {policies[0]?.prohibitedPaths.map((path) => (
                <span key={path}>{path}</span>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </section>
  );
}

function PolicyPanel({ items, title }: { items: DomesticPlatformPolicy[]; title: string }) {
  return (
    <section className="panel">
      <div className="sourcePanelHeader">
        <div>
          <p className="eyebrow">{title}</p>
          <h2>{title}</h2>
        </div>
        <span className="statusBadge">{items.length}</span>
      </div>
      <div className="logTable">
        {items.map((item) => (
          <div className="logRow" key={item.platform}>
            <strong>{item.platform}</strong>
            <span>{item.automationLevel}</span>
            <small>
              {item.allowedPaths.join(" / ")} / {item.requiresApproval ? "需审核" : "免审核"} / {item.notes}
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
