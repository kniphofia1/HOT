import { revalidatePath } from "next/cache";
import {
  BriefExport,
  EventCluster,
  Source,
  TeamSummary,
  fetchJson,
  formatDateTime,
  postJsonBody,
} from "../../lib/api";

export const dynamic = "force-dynamic";

async function createUserAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/team/users", {
    displayName: stringValue(formData, "displayName"),
    email: optionalStringValue(formData, "email"),
    role: stringValue(formData, "role", "analyst"),
  });
  revalidatePath("/team");
}

async function createSpaceAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/team/spaces", {
    name: stringValue(formData, "name"),
    description: optionalStringValue(formData, "description"),
    actorUserId: optionalStringValue(formData, "actorUserId"),
  });
  revalidatePath("/team");
}

async function createBookmarkAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/team/bookmarks", {
    spaceId: stringValue(formData, "spaceId"),
    userId: stringValue(formData, "userId"),
    eventClusterId: stringValue(formData, "eventClusterId"),
    note: optionalStringValue(formData, "note"),
  });
  revalidatePath("/team");
}

async function createAnnotationAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/team/annotations", {
    spaceId: stringValue(formData, "spaceId"),
    userId: stringValue(formData, "userId"),
    eventClusterId: stringValue(formData, "eventClusterId"),
    label: stringValue(formData, "label", "note"),
    note: stringValue(formData, "note"),
  });
  revalidatePath("/team");
}

async function createReviewAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/team/brief-reviews", {
    spaceId: stringValue(formData, "spaceId"),
    briefExportId: stringValue(formData, "briefExportId"),
    requestedByUserId: stringValue(formData, "requestedByUserId"),
    reviewerUserId: optionalStringValue(formData, "reviewerUserId"),
    notes: optionalStringValue(formData, "notes"),
  });
  revalidatePath("/team");
}

async function createSourceLinkAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/team/source-links", {
    spaceId: stringValue(formData, "spaceId"),
    sourceId: stringValue(formData, "sourceId"),
    actorUserId: optionalStringValue(formData, "actorUserId"),
  });
  revalidatePath("/team");
}

export default async function TeamPage() {
  let summary: TeamSummary | null = null;
  let sources: Source[] = [];
  let clusters: EventCluster[] = [];
  let exports: BriefExport[] = [];
  let error: string | null = null;

  try {
    [summary, sources, clusters, exports] = await Promise.all([
      fetchJson<TeamSummary>("/api/team/summary"),
      fetchJson<Source[]>("/api/sources"),
      fetchJson<EventCluster[]>("/api/clusters?sort=score"),
      fetchJson<BriefExport[]>("/api/briefs/exports"),
    ]);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取团队协作数据";
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Team Room</p>
        <h1>团队情报室</h1>
        <p>本地团队用户、空间、共享信源、事件收藏、人工标注、简报审核和审计日志。</p>
      </header>

      {error || !summary ? <StatePanel title="无法读取团队协作数据" detail={error || "暂无数据"} /> : null}

      {summary ? (
        <>
          <div className="metricStrip">
            <div>
              <span>用户</span>
              <strong>{summary.users.length}</strong>
            </div>
            <div>
              <span>空间</span>
              <strong>{summary.spaces.length}</strong>
            </div>
            <div>
              <span>标注</span>
              <strong>{summary.annotations.length}</strong>
            </div>
          </div>

          <div className="panelGrid">
            <section className="panel">
              <h2>创建用户</h2>
              <form action={createUserAction} className="sourceForm">
                <label className="fieldStack">
                  姓名
                  <input name="displayName" required />
                </label>
                <label className="fieldStack">
                  邮箱
                  <input name="email" type="email" />
                </label>
                <label className="fieldStack">
                  角色
                  <select name="role" defaultValue="analyst">
                    <option value="analyst">analyst</option>
                    <option value="reviewer">reviewer</option>
                    <option value="owner">owner</option>
                  </select>
                </label>
                <button type="submit">创建用户</button>
              </form>
            </section>

            <section className="panel">
              <h2>创建空间</h2>
              <form action={createSpaceAction} className="sourceForm">
                <label className="fieldStack">
                  名称
                  <input name="name" required />
                </label>
                <label className="fieldStack">
                  创建人
                  <SelectUser name="actorUserId" users={summary.users} />
                </label>
                <label className="fieldStack">
                  描述
                  <textarea name="description" />
                </label>
                <button type="submit">创建空间</button>
              </form>
            </section>
          </div>

          <section className="panel">
            <h2>协作动作</h2>
            <div className="panelGrid">
              <form action={createSourceLinkAction} className="sourceForm">
                <h3>共享信源</h3>
                <SelectSpace spaces={summary.spaces} />
                <SelectSource sources={sources} />
                <SelectUser name="actorUserId" users={summary.users} />
                <button type="submit">共享</button>
              </form>
              <form action={createBookmarkAction} className="sourceForm">
                <h3>收藏事件</h3>
                <SelectSpace spaces={summary.spaces} />
                <SelectUser name="userId" users={summary.users} />
                <SelectEvent clusters={clusters} />
                <textarea name="note" placeholder="收藏备注" />
                <button type="submit">收藏</button>
              </form>
              <form action={createAnnotationAction} className="sourceForm">
                <h3>人工标注</h3>
                <SelectSpace spaces={summary.spaces} />
                <SelectUser name="userId" users={summary.users} />
                <SelectEvent clusters={clusters} />
                <input name="label" placeholder="标签，例如 risk" required />
                <textarea name="note" placeholder="标注说明" required />
                <button type="submit">标注</button>
              </form>
              <form action={createReviewAction} className="sourceForm">
                <h3>简报审核</h3>
                <SelectSpace spaces={summary.spaces} />
                <SelectBrief exports={exports} />
                <SelectUser name="requestedByUserId" users={summary.users} />
                <SelectUser name="reviewerUserId" users={summary.users} />
                <textarea name="notes" placeholder="审核说明" />
                <button type="submit">提交审核</button>
              </form>
            </div>
          </section>

          <section className="panel">
            <h2>审计日志</h2>
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

function SelectSpace({ spaces }: { spaces: TeamSummary["spaces"] }) {
  return (
    <select name="spaceId" required>
      {spaces.map((space) => (
        <option key={space.id} value={space.id}>
          {space.name}
        </option>
      ))}
    </select>
  );
}

function SelectSource({ sources }: { sources: Source[] }) {
  return (
    <select name="sourceId" required>
      {sources.map((source) => (
        <option key={source.id} value={source.id}>
          {source.name}
        </option>
      ))}
    </select>
  );
}

function SelectEvent({ clusters }: { clusters: EventCluster[] }) {
  return (
    <select name="eventClusterId" required>
      {clusters.map((cluster) => (
        <option key={cluster.id} value={cluster.id}>
          {cluster.displayTitle}
        </option>
      ))}
    </select>
  );
}

function SelectBrief({ exports }: { exports: BriefExport[] }) {
  return (
    <select name="briefExportId" required>
      {exports.map((item) => (
        <option key={item.id} value={item.id}>
          {item.title}
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
