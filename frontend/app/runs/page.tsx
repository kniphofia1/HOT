import { AiRun, FetchRun, fetchJson } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  let fetchRuns: FetchRun[] = [];
  let aiRuns: AiRun[] = [];
  let error: string | null = null;

  try {
    [fetchRuns, aiRuns] = await Promise.all([
      fetchJson<FetchRun[]>("/api/runs/fetch"),
      fetchJson<AiRun[]>("/api/runs/ai"),
    ]);
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取运行日志";
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Runs</p>
        <h1>运行日志</h1>
        <p>查看信源抓取和 AI 聚类摘要的运行状态。</p>
      </header>

      {error ? <StatePanel title="无法读取日志" detail={error} /> : null}

      {!error ? (
        <div className="panelGrid">
          <LogPanel title="FetchRun">
            {fetchRuns.length === 0 ? (
              <p>暂无抓取记录。</p>
            ) : (
              <div className="logTable">
                {fetchRuns.map((run) => (
                  <div className="logRow" key={run.id}>
                    <strong>{run.status}</strong>
                    <span>{run.itemsCreated}/{run.itemsFound}</span>
                    <small>{run.errorMessage || run.sourceId}</small>
                  </div>
                ))}
              </div>
            )}
          </LogPanel>
          <LogPanel title="AiRunLog">
            {aiRuns.length === 0 ? (
              <p>暂无 AI 运行记录。</p>
            ) : (
              <div className="logTable">
                {aiRuns.map((run) => (
                  <div className="logRow" key={run.id}>
                    <strong>{run.status}</strong>
                    <span>{run.model || "未配置模型"}</span>
                    <small>{run.errorMessage || run.inputHash}</small>
                  </div>
                ))}
              </div>
            )}
          </LogPanel>
        </div>
      ) : null}
    </section>
  );
}

function LogPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
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
