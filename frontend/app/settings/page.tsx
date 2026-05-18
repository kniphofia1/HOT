import { revalidatePath } from "next/cache";
import {
  AutomationRunLog,
  AutomationRunResult,
  AutomationSettings,
  BriefTemplate,
  LocalCredential,
  MaintenanceHealth,
  PUBLIC_API_BASE_URL,
  deleteJson,
  fetchJson,
  formatDateTime,
  patchJsonBody,
  postJsonBody,
} from "../../lib/api";

export const dynamic = "force-dynamic";

async function saveCredentialAction(formData: FormData) {
  "use server";
  await postJsonBody<LocalCredential>("/api/maintenance/credentials", {
    key: stringValue(formData, "key"),
    label: stringValue(formData, "label"),
    provider: optionalStringValue(formData, "provider"),
    environmentKey: optionalStringValue(formData, "environmentKey"),
    notes: optionalStringValue(formData, "notes"),
  });
  revalidatePath("/settings");
}

async function deleteCredentialAction(formData: FormData) {
  "use server";
  if (formData.get("confirmDelete") !== "on") {
    return;
  }
  await deleteJson(`/api/maintenance/credentials/${stringValue(formData, "credentialId")}`);
  revalidatePath("/settings");
}

async function updateTemplateAction(formData: FormData) {
  "use server";
  await patchJsonBody<BriefTemplate>(`/api/briefs/templates/${stringValue(formData, "templateId")}`, {
    name: stringValue(formData, "name"),
    sectionsJson: stringValue(formData, "sections")
      .split("\n")
      .map((section) => section.trim())
      .filter(Boolean),
    styleRules: optionalStringValue(formData, "styleRules"),
  });
  revalidatePath("/settings");
  revalidatePath("/briefs");
}

async function updateAutomationAction(formData: FormData) {
  "use server";
  await patchJsonBody<AutomationSettings>("/api/automation/settings", {
    sourceRefreshEnabled: formData.get("sourceRefreshEnabled") === "on",
    dailyReportsEnabled: formData.get("dailyReportsEnabled") === "on",
    dailyRunTime: stringValue(formData, "dailyRunTime", "08:30"),
    timezone: stringValue(formData, "timezone", "Asia/Shanghai"),
    globalMaxEvents: numberValue(formData, "globalMaxEvents", 30),
    industryMaxEvents: numberValue(formData, "industryMaxEvents", 12),
  });
  revalidatePath("/settings");
  revalidatePath("/industry");
}

async function runAutomationAction(formData: FormData) {
  "use server";
  await postJsonBody<AutomationRunResult>("/api/automation/run", {
    task: stringValue(formData, "task", "all"),
  });
  revalidatePath("/settings");
  revalidatePath("/industry");
}

export default async function SettingsPage() {
  let health: MaintenanceHealth | null = null;
  let credentials: LocalCredential[] = [];
  let templates: BriefTemplate[] = [];
  let automation: AutomationSettings | null = null;
  let automationRuns: AutomationRunLog[] = [];
  let error: string | null = null;

  try {
    [health, credentials, templates, automation, automationRuns] = await Promise.all([
      fetchJson<MaintenanceHealth>("/api/maintenance/health"),
      fetchJson<LocalCredential[]>("/api/maintenance/credentials"),
      fetchJson<BriefTemplate[]>("/api/briefs/templates"),
      fetchJson<AutomationSettings>("/api/automation/settings"),
      fetchJson<AutomationRunLog[]>("/api/automation/runs?take=12"),
    ]);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取设置";
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Local Settings</p>
        <h1>设置</h1>
        <p>本地稳定版控制台，用于查看信源健康、导出备份、登记凭证引用和维护简报模板。</p>
      </header>

      {error ? <StatePanel title="无法读取设置" detail={error} /> : null}

      {!error && health ? (
        <>
          <section className="metricStrip">
            <div>
              <span>系统状态</span>
              <strong>{health.status}</strong>
            </div>
            <div>
              <span>启用信源</span>
              <strong>
                {health.enabledSourceCount}/{health.sourceCount}
              </strong>
            </div>
            <div>
              <span>异常信源</span>
              <strong>{health.failingSourceCount}</strong>
            </div>
          </section>

          <div className="panelGrid">
            <section className="panel">
              <div className="sourcePanelHeader">
                <div>
                  <p className="eyebrow">Health</p>
                  <h2>信源健康</h2>
                </div>
                <span className={health.status === "ok" ? "statusBadge" : "statusBadge off"}>
                  {formatDateTime(health.generatedAt)}
                </span>
              </div>
              {health.sources.length === 0 ? (
                <p>暂无信源。</p>
              ) : (
                <div className="logTable">
                  {health.sources.map((source) => (
                    <div className="logRow" key={source.sourceId}>
                      <strong>{source.status}</strong>
                      <span>{source.type}</span>
                      <small>
                        {source.name} / 失败 {source.consecutiveFailures} 次 / 下次{" "}
                        {formatDateTime(source.nextFetchAt)}
                      </small>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="panel">
              <div className="sourcePanelHeader">
                <div>
                  <p className="eyebrow">Backup</p>
                  <h2>数据备份</h2>
                </div>
                <a className="buttonLink" href={`${PUBLIC_API_BASE_URL}/api/maintenance/backup/download`}>
                  下载 JSON
                </a>
              </div>
              <p>备份包含当前 SQLite 数据表内容；恢复接口为 `/api/maintenance/restore`，按主键合并导入。</p>
            </section>
          </div>

          {automation ? (
            <section className="panel">
              <div className="sourcePanelHeader">
                <div>
                  <p className="eyebrow">Automation</p>
                  <h2>自动化运行</h2>
                </div>
                <form action={runAutomationAction} className="inlineActions">
                  <input name="task" type="hidden" value="all" />
                  <button type="submit">立即运行</button>
                </form>
              </div>
              <AutomationSettingsForm automation={automation} />
              <div className="logTable">
                {automationRuns.length === 0 ? (
                  <p className="mutedNote">暂无自动化运行记录。</p>
                ) : (
                  automationRuns.map((run) => (
                    <div className="logRow" key={run.id}>
                      <strong>{run.status}</strong>
                      <span>{run.taskType}</span>
                      <small>
                        {formatDateTime(run.startedAt)} / {run.errorMessage || "运行完成"}
                      </small>
                    </div>
                  ))
                )}
              </div>
            </section>
          ) : null}

          <section className="panel">
            <div className="sourcePanelHeader">
              <div>
                <p className="eyebrow">Credentials</p>
                <h2>凭证引用</h2>
              </div>
              <span className="statusBadge">{credentials.length} 个引用</span>
            </div>
            <form action={saveCredentialAction} className="sourceForm">
              <div className="sourceFormGrid">
                <label className="fieldStack">
                  Key
                  <input name="key" placeholder="openai_api_key" required />
                </label>
                <label className="fieldStack">
                  名称
                  <input name="label" placeholder="OpenAI API Key" required />
                </label>
                <label className="fieldStack">
                  Provider
                  <input name="provider" placeholder="openai" />
                </label>
                <label className="fieldStack">
                  环境变量
                  <input name="environmentKey" placeholder="AI_API_KEY" />
                </label>
              </div>
              <label className="fieldStack">
                备注
                <textarea name="notes" placeholder="用途、来源或轮换说明" />
              </label>
              <button type="submit">保存引用</button>
            </form>

            <div className="sourceInstanceList">
              {credentials.length === 0 ? (
                <p className="mutedNote">暂无凭证引用。</p>
              ) : (
                credentials.map((credential) => (
                  <div className="sourceInstance" key={credential.id}>
                    <div className="sourceInstanceMain">
                      <div className="sourceInstanceTitle">
                        <strong>{credential.label}</strong>
                        <span className={credential.configured ? "statusBadge" : "statusBadge off"}>
                          {credential.configured ? "已配置" : "未配置"}
                        </span>
                      </div>
                      <small>
                        {credential.key} / {credential.provider || "未分类"} /{" "}
                        {credential.environmentKey || "未绑定环境变量"}
                      </small>
                      {credential.secretHint ? <small>{credential.secretHint}</small> : null}
                      {credential.notes ? <small>{credential.notes}</small> : null}
                    </div>
                    <form action={deleteCredentialAction} className="deleteSourceForm">
                      <input name="credentialId" type="hidden" value={credential.id} />
                      <label className="confirmLine">
                        <input name="confirmDelete" required type="checkbox" />
                        确认删除
                      </label>
                      <button className="dangerButton" type="submit">
                        删除
                      </button>
                    </form>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="panel">
            <div className="sourcePanelHeader">
              <div>
                <p className="eyebrow">Brief Templates</p>
                <h2>简报模板</h2>
              </div>
              <span className="statusBadge">{templates.length} 个模板</span>
            </div>
            <div className="sourceInstanceList">
              {templates.map((template) => (
                <form action={updateTemplateAction} className="sourceForm" key={template.id}>
                  <input name="templateId" type="hidden" value={template.id} />
                  <div className="sourceFormGrid">
                    <label className="fieldStack">
                      名称
                      <input defaultValue={template.name} name="name" required />
                    </label>
                    <label className="fieldStack">
                      Mode
                      <input defaultValue={template.mode} disabled />
                    </label>
                  </div>
                  <label className="fieldStack">
                    章节
                    <textarea defaultValue={template.sectionsJson.join("\n")} name="sections" required />
                  </label>
                  <label className="fieldStack">
                    样式规则
                    <textarea defaultValue={template.styleRules || ""} name="styleRules" />
                  </label>
                  <button type="submit">更新模板</button>
                </form>
              ))}
            </div>
          </section>
        </>
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

function AutomationSettingsForm({ automation }: { automation: AutomationSettings }) {
  const source = automation.schedules.find((schedule) => schedule.taskType === "source_refresh");
  const daily = automation.schedules.find((schedule) => schedule.taskType === "daily_reports");
  return (
    <form action={updateAutomationAction} className="sourceForm">
      <div className="sourceFormGrid">
        <label className="checkboxLine">
          <input defaultChecked={source?.enabled ?? true} name="sourceRefreshEnabled" type="checkbox" />
          <span>启用定时抓取</span>
        </label>
        <label className="checkboxLine">
          <input defaultChecked={daily?.enabled ?? true} name="dailyReportsEnabled" type="checkbox" />
          <span>启用行业日报</span>
        </label>
        <label className="fieldStack">
          行业日报时间
          <input defaultValue={daily?.runTime || "08:30"} name="dailyRunTime" pattern="\d{2}:\d{2}" required />
        </label>
        <label className="fieldStack">
          时区
          <input defaultValue={daily?.timezone || "Asia/Shanghai"} name="timezone" required />
        </label>
        <input name="globalMaxEvents" type="hidden" value={String(daily?.configJson.globalMaxEvents ?? 30)} />
        <label className="fieldStack">
          单行业事件上限
          <input defaultValue={String(daily?.configJson.industryMaxEvents ?? 12)} min={1} max={50} name="industryMaxEvents" type="number" />
        </label>
      </div>
      <div className="automationStatus">
        <span>下次抓取：{formatDateTime(source?.nextRunAt ?? null)}</span>
        <span>下次行业日报：{formatDateTime(daily?.nextRunAt ?? null)}</span>
      </div>
      <button type="submit">保存自动化设置</button>
    </form>
  );
}

function stringValue(formData: FormData, key: string, fallback = ""): string {
  const value = formData.get(key);
  if (typeof value !== "string" || !value.trim()) {
    return fallback;
  }
  return value.trim();
}

function numberValue(formData: FormData, key: string, fallback: number): number {
  const value = Number(formData.get(key));
  return Number.isFinite(value) ? value : fallback;
}

function optionalStringValue(formData: FormData, key: string): string | null {
  const value = stringValue(formData, key);
  return value || null;
}
