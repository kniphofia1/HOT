import { revalidatePath } from "next/cache";
import { TeamSummary, fetchJson, formatDateTime, postJsonBody } from "../../lib/api";

export const dynamic = "force-dynamic";

type SaasSummary = {
  organizations: Array<{ id: string; name: string; slug: string; status: string; createdAt: string }>;
  memberships: Array<{ id: string; organizationId: string; userId: string; role: string; permissionsJson: string[] }>;
  plans: Array<{ id: string; name: string; code: string; priceCents: number; quotaJson: Record<string, number> }>;
  subscriptions: Array<{ id: string; organizationId: string; planId: string; status: string }>;
  quotaUsage: Array<{ id: string; organizationId: string; metric: string; used: number; limit: number; overLimit: boolean }>;
  tasks: Array<{ id: string; organizationId: string | null; taskType: string; status: string; priority: number }>;
  alerts: Array<{ id: string; organizationId: string; name: string; metric: string; threshold: number; status: string }>;
  dataScopes: Array<{ id: string; organizationId: string; entityType: string; entityId: string; accessLevel: string }>;
  auditLogs: Array<{ id: string; organizationId: string | null; action: string; entityType: string; entityId: string; createdAt: string }>;
};

async function createOrganizationAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/saas/organizations", {
    name: stringValue(formData, "name"),
    slug: stringValue(formData, "slug"),
    actorUserId: optionalStringValue(formData, "actorUserId"),
  });
  revalidatePath("/saas");
}

async function createPlanAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/saas/plans", {
    name: stringValue(formData, "name"),
    code: stringValue(formData, "code"),
    priceCents: numberValue(formData, "priceCents", 0),
    quotaJson: {
      sources: numberValue(formData, "sourcesQuota", 100),
      aiRuns: numberValue(formData, "aiRunsQuota", 10000),
    },
  });
  revalidatePath("/saas");
}

async function createTaskAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/saas/tasks", {
    organizationId: optionalStringValue(formData, "organizationId"),
    taskType: stringValue(formData, "taskType", "refresh_sources"),
    priority: numberValue(formData, "priority", 0),
    payloadJson: {},
    actorUserId: optionalStringValue(formData, "actorUserId"),
  });
  revalidatePath("/saas");
}

async function createAlertAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/saas/alerts", {
    organizationId: stringValue(formData, "organizationId"),
    name: stringValue(formData, "name"),
    metric: stringValue(formData, "metric", "aiRuns"),
    threshold: numberValue(formData, "threshold", 90),
    actorUserId: optionalStringValue(formData, "actorUserId"),
  });
  revalidatePath("/saas");
}

export default async function SaasPage() {
  let summary: SaasSummary | null = null;
  let team: TeamSummary | null = null;
  let error: string | null = null;

  try {
    [summary, team] = await Promise.all([
      fetchJson<SaasSummary>("/api/saas/summary"),
      fetchJson<TeamSummary>("/api/team/summary"),
    ]);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取 SaaS 控制平面";
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">SaaS Control Plane</p>
        <h1>SaaS 控制台</h1>
        <p>组织、角色、套餐、配额、任务队列、监控告警、租户数据归属和商业化审计。</p>
      </header>

      {error || !summary || !team ? <StatePanel title="无法读取 SaaS 控制平面" detail={error || "暂无数据"} /> : null}

      {summary && team ? (
        <>
          <div className="metricStrip">
            <div>
              <span>组织</span>
              <strong>{summary.organizations.length}</strong>
            </div>
            <div>
              <span>任务</span>
              <strong>{summary.tasks.length}</strong>
            </div>
            <div>
              <span>告警</span>
              <strong>{summary.alerts.length}</strong>
            </div>
          </div>

          <div className="panelGrid">
            <section className="panel">
              <h2>创建组织</h2>
              <form action={createOrganizationAction} className="sourceForm">
                <input name="name" placeholder="Acme Intelligence" required />
                <input name="slug" placeholder="acme" required />
                <SelectUser users={team.users} name="actorUserId" />
                <button type="submit">创建组织</button>
              </form>
            </section>
            <section className="panel">
              <h2>创建套餐</h2>
              <form action={createPlanAction} className="sourceForm">
                <input name="name" placeholder="Pro" required />
                <input name="code" placeholder="pro" required />
                <input name="priceCents" placeholder="9900" type="number" />
                <input name="sourcesQuota" placeholder="信源配额" type="number" />
                <input name="aiRunsQuota" placeholder="AI 调用配额" type="number" />
                <button type="submit">创建套餐</button>
              </form>
            </section>
          </div>

          <div className="panelGrid">
            <section className="panel">
              <h2>任务队列</h2>
              <form action={createTaskAction} className="sourceForm">
                <SelectOrganization organizations={summary.organizations} />
                <input name="taskType" defaultValue="refresh_sources" />
                <input name="priority" defaultValue="0" type="number" />
                <SelectUser users={team.users} name="actorUserId" />
                <button type="submit">加入队列</button>
              </form>
            </section>
            <section className="panel">
              <h2>监控告警</h2>
              <form action={createAlertAction} className="sourceForm">
                <SelectOrganization organizations={summary.organizations} />
                <input name="name" placeholder="AI quota" required />
                <input name="metric" defaultValue="aiRuns" />
                <input name="threshold" defaultValue="90" type="number" />
                <SelectUser users={team.users} name="actorUserId" />
                <button type="submit">创建告警</button>
              </form>
            </section>
          </div>

          <section className="panel">
            <h2>配额与任务</h2>
            <div className="logTable">
              {summary.quotaUsage.map((item) => (
                <div className="logRow" key={item.id}>
                  <strong>{item.metric}</strong>
                  <span>{item.overLimit ? "over" : "ok"}</span>
                  <small>{item.used} / {item.limit}</small>
                </div>
              ))}
              {summary.tasks.map((task) => (
                <div className="logRow" key={task.id}>
                  <strong>{task.taskType}</strong>
                  <span>{task.status}</span>
                  <small>priority {task.priority}</small>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>SaaS 审计</h2>
            <div className="logTable">
              {summary.auditLogs.map((log) => (
                <div className="logRow" key={log.id}>
                  <strong>{log.action}</strong>
                  <span>{log.entityType}</span>
                  <small>{formatDateTime(log.createdAt)} / {log.entityId}</small>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </section>
  );
}

function SelectOrganization({ organizations }: { organizations: SaasSummary["organizations"] }) {
  return (
    <select name="organizationId" required>
      {organizations.map((organization) => (
        <option key={organization.id} value={organization.id}>
          {organization.name}
        </option>
      ))}
    </select>
  );
}

function SelectUser({ users, name }: { users: TeamSummary["users"]; name: string }) {
  return (
    <select name={name} defaultValue="">
      <option value="">未选择</option>
      {users.map((user) => (
        <option key={user.id} value={user.id}>
          {user.displayName}
        </option>
      ))}
    </select>
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

function numberValue(formData: FormData, key: string, fallback: number): number {
  const parsed = Number(stringValue(formData, key));
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}
