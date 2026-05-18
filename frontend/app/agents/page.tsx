import { revalidatePath } from "next/cache";
import { fetchJson, formatDateTime, postJson, postJsonBody } from "../../lib/api";

export const dynamic = "force-dynamic";

type Agent = {
  id: string;
  name: string;
  agentType: string;
  scopeJson: Record<string, unknown>;
  enabled: boolean;
  cadenceMinutes: number;
  lastRunAt: string | null;
};

type AgentAlert = {
  id: string;
  agentId: string;
  eventClusterId: string;
  severity: string;
  title: string;
  reason: string;
  followUpQuestionsJson: string[];
  status: string;
  createdAt: string;
};

type AgentRun = {
  id: string;
  agentId: string;
  status: string;
  clustersScanned: number;
  alertsCreated: number;
  errorMessage: string | null;
  createdAt: string;
};

async function createAgentAction(formData: FormData) {
  "use server";
  await postJsonBody("/api/agents", {
    name: stringValue(formData, "name"),
    agentType: stringValue(formData, "agentType", "topic"),
    scopeJson: {
      keywords: splitList(formData, "keywords"),
      entities: splitList(formData, "entities"),
      domains: splitList(formData, "domains"),
      minHotScore: numberValue(formData, "minHotScore", 0),
      minPropagationScore: numberValue(formData, "minPropagationScore", 0),
    },
    cadenceMinutes: numberValue(formData, "cadenceMinutes", 60),
  });
  revalidatePath("/agents");
}

async function runAgentsAction() {
  "use server";
  await postJson("/api/agents/run");
  revalidatePath("/agents");
}

async function runAgentAction(formData: FormData) {
  "use server";
  await postJson(`/api/agents/${stringValue(formData, "agentId")}/run`);
  revalidatePath("/agents");
}

export default async function AgentsPage() {
  let agents: Agent[] = [];
  let alerts: AgentAlert[] = [];
  let runs: AgentRun[] = [];
  let error: string | null = null;

  try {
    [agents, alerts, runs] = await Promise.all([
      fetchJson<Agent[]>("/api/agents"),
      fetchJson<AgentAlert[]>("/api/agents/alerts"),
      fetchJson<AgentRun[]>("/api/agents/runs"),
    ]);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取 Agent 情报官";
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Agent Intelligence Officer</p>
        <h1>Agent 情报官</h1>
        <p>按主题、公司、竞品、投资赛道和风险范围主动扫描事件，生成系统内预警和跟进问题。</p>
      </header>

      {error ? <StatePanel title="无法读取 Agent 情报官" detail={error} /> : null}

      {!error ? (
        <>
          <div className="metricStrip">
            <div>
              <span>Agent</span>
              <strong>{agents.length}</strong>
            </div>
            <div>
              <span>预警</span>
              <strong>{alerts.length}</strong>
            </div>
            <div>
              <span>运行</span>
              <strong>{runs.length}</strong>
            </div>
          </div>

          <section className="panel">
            <div className="sourcePanelHeader">
              <div>
                <p className="eyebrow">Create Agent</p>
                <h2>创建 Agent</h2>
              </div>
              <form action={runAgentsAction}>
                <button type="submit">运行全部</button>
              </form>
            </div>
            <form action={createAgentAction} className="sourceForm">
              <div className="sourceFormGrid">
                <input name="name" placeholder="OpenAI risk agent" required />
                <select name="agentType" defaultValue="topic">
                  <option value="topic">主题</option>
                  <option value="company">公司</option>
                  <option value="competitor">竞品</option>
                  <option value="investment">投资赛道</option>
                  <option value="risk">风险</option>
                  <option value="anomaly">异常扩散</option>
                </select>
                <input name="keywords" placeholder="关键词，逗号分隔" />
                <input name="entities" placeholder="实体，逗号分隔" />
                <input name="domains" placeholder="领域代码，逗号分隔" />
                <input name="minHotScore" placeholder="最低热度" type="number" />
                <input name="minPropagationScore" placeholder="最低传播" type="number" />
                <input name="cadenceMinutes" defaultValue="60" type="number" />
              </div>
              <button type="submit">创建</button>
            </form>
          </section>

          <section className="panel">
            <h2>Agent 列表</h2>
            <div className="logTable">
              {agents.map((agent) => (
                <div className="logRow" key={agent.id}>
                  <strong>{agent.name}</strong>
                  <span>{agent.agentType}</span>
                  <small>
                    {agent.enabled ? "enabled" : "disabled"} / 最近运行 {formatDateTime(agent.lastRunAt)}
                    <form action={runAgentAction}>
                      <input name="agentId" type="hidden" value={agent.id} />
                      <button className="secondaryButton" type="submit">运行</button>
                    </form>
                  </small>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            <h2>预警</h2>
            <div className="evidenceList">
              {alerts.map((alert) => (
                <article className="evidenceItem" key={alert.id}>
                  <div className="eventMeta">{alert.severity} / {alert.status} / {formatDateTime(alert.createdAt)}</div>
                  <h3>{alert.title}</h3>
                  <p>{alert.reason}</p>
                  <div className="tagRow">
                    {alert.followUpQuestionsJson.slice(0, 3).map((question) => (
                      <span key={question}>{question}</span>
                    ))}
                  </div>
                </article>
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

function stringValue(formData: FormData, key: string, fallback = ""): string {
  const value = formData.get(key);
  if (typeof value !== "string" || !value.trim()) {
    return fallback;
  }
  return value.trim();
}

function splitList(formData: FormData, key: string): string[] {
  return stringValue(formData, key)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function numberValue(formData: FormData, key: string, fallback: number): number {
  const parsed = Number(stringValue(formData, key));
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}
