"use client";

import Link from "next/link";
import { Download, FileText, RefreshCcw, Wand2 } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

type ReportGenerateResponse = {
  exportId: string;
  title: string;
  markdown: string;
  eventClusterIds: string[];
  generatedAt: string;
  aiStatus: string;
  aiError: string | null;
};

type RetryFailedSourcesResponse = {
  attemptedCount: number;
  skippedCount: number;
  successCount: number;
  failedCount: number;
  errors: string[];
};

type FormState = {
  industry: string;
  timeRange: string;
  startDate: string;
  endDate: string;
  reportType: string;
  modules: string[];
  outputFormat: string;
  style: string;
};

const industryOptions = [
  { label: "AI", value: "ai", description: "全局 AI 动态：模型、产品、AI 公司、开源生态和工具链。" },
  {
    label: "半导体",
    value: "semiconductor",
    description: "GPU、AI 芯片、HBM、先进封装、数据中心和资本开支。",
  },
  { label: "具身智能", value: "embodied_ai", description: "人形机器人、工业机器人、机器人基础模型和量产交付。" },
  { label: "新能源", value: "energy", description: "数据中心用电、电网、储能、绿电和电池。" },
  { label: "技术", value: "technology", description: "编程语言、数据库、云原生、开源基础设施、网络安全、操作系统和开发者工具。" },
  { label: "产品", value: "products", description: "AI 产品、软件产品、电脑、手机、消费电子、硬件新品和平台功能更新。" },
];

const timeRangeOptions = [
  { label: "今日", value: "today" },
  { label: "本周", value: "this_week" },
  { label: "自定义", value: "custom" },
];

const reportTypeOptions = [
  { label: "日报", value: "daily" },
  { label: "周报", value: "weekly" },
  { label: "竞品简报", value: "competitive_brief" },
  { label: "投资机会", value: "investment_opportunity" },
  { label: "风险预警", value: "risk_alert" },
];

const moduleOptions = [
  { label: "核心结论", value: "core_conclusions" },
  { label: "重要事件", value: "important_events" },
  { label: "公司动态", value: "company_updates" },
  { label: "技术进展", value: "technology_progress" },
  { label: "政策监管", value: "policy_regulation" },
  { label: "风险信号", value: "risk_signals" },
];

const outputFormatOptions = [
  { label: "Markdown", value: "markdown", enabled: true },
  { label: "Word", value: "docx", enabled: false },
  { label: "PDF", value: "pdf", enabled: false },
  { label: "PPTX", value: "pptx", enabled: false },
];

const styleOptions = [
  { label: "简洁版", value: "concise" },
  { label: "咨询报告版", value: "consulting" },
  { label: "老板汇报版", value: "executive" },
];

const defaultForm: FormState = {
  industry: "ai",
  timeRange: "today",
  startDate: "",
  endDate: "",
  reportType: "daily",
  modules: ["core_conclusions", "important_events", "company_updates", "technology_progress", "risk_signals"],
  outputFormat: "markdown",
  style: "consulting",
};

export default function ReportCenterPage() {
  const [form, setForm] = useState<FormState>(defaultForm);
  const [result, setResult] = useState<ReportGenerateResponse | null>(null);
  const [retryResult, setRetryResult] = useState<RetryFailedSourcesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  const activeIndustry = useMemo(
    () => industryOptions.find((item) => item.value === form.industry) ?? industryOptions[0],
    [form.industry],
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsGenerating(true);
    setError(null);
    try {
      const response = await fetch("/api/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry: form.industry,
          timeRange: form.timeRange,
          startDate: form.timeRange === "custom" ? form.startDate || null : null,
          endDate: form.timeRange === "custom" ? form.endDate || null : null,
          reportType: form.reportType,
          modules: form.modules,
          outputFormat: form.outputFormat,
          style: form.style,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
      }
      setResult((await response.json()) as ReportGenerateResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "生成失败");
    } finally {
      setIsGenerating(false);
    }
  }

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function toggleModule(value: string) {
    setForm((current) => {
      const exists = current.modules.includes(value);
      return {
        ...current,
        modules: exists ? current.modules.filter((item) => item !== value) : [...current.modules, value],
      };
    });
  }

  async function retryFailedSources() {
    setIsRetrying(true);
    setRetryError(null);
    try {
      const response = await fetch("/api/sources/retry-failed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry: form.industry,
          includeCredentialed: false,
          runPipeline: false,
          limit: 5,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
      }
      setRetryResult((await response.json()) as RetryFailedSourcesResponse);
    } catch (caught) {
      setRetryError(caught instanceof Error ? caught.message : "重试失败");
    } finally {
      setIsRetrying(false);
    }
  }

  return (
    <section className="reportCenter pageStack">
      <header className="pageHeader reportHeader">
        <p className="eyebrow">Report Center</p>
        <h1>报告中心</h1>
        <p>选择行业、时间范围、报告类型和内容模块，生成可回溯事件驱动的 Markdown 报告。</p>
      </header>

      <div className="reportLayout">
        <form className="panel reportFormPanel" onSubmit={submit}>
          <section className="reportControlBlock">
            <div className="reportBlockHead">
              <span>01</span>
              <h2>选择行业</h2>
            </div>
            <div className="reportOptionGrid industries">
              {industryOptions.map((option) => (
                <label className={form.industry === option.value ? "reportRadio active" : "reportRadio"} key={option.value}>
                  <input
                    checked={form.industry === option.value}
                    name="industry"
                    onChange={() => updateField("industry", option.value)}
                    type="radio"
                    value={option.value}
                  />
                  <strong>{option.label}</strong>
                  <small>{option.description}</small>
                </label>
              ))}
            </div>
          </section>

          <section className="reportControlBlock">
            <div className="reportBlockHead">
              <span>02</span>
              <h2>报告配置</h2>
            </div>
            <div className="reportFieldGrid">
              <label className="fieldStack">
                时间范围
                <select value={form.timeRange} onChange={(event) => updateField("timeRange", event.target.value)}>
                  {timeRangeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="fieldStack">
                报告类型
                <select value={form.reportType} onChange={(event) => updateField("reportType", event.target.value)}>
                  {reportTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="fieldStack">
                风格
                <select value={form.style} onChange={(event) => updateField("style", event.target.value)}>
                  {styleOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              {form.timeRange === "custom" ? (
                <>
                  <label className="fieldStack">
                    开始日期
                    <input
                      type="date"
                      value={form.startDate}
                      onChange={(event) => updateField("startDate", event.target.value)}
                    />
                  </label>
                  <label className="fieldStack">
                    结束日期
                    <input
                      type="date"
                      value={form.endDate}
                      onChange={(event) => updateField("endDate", event.target.value)}
                    />
                  </label>
                </>
              ) : null}
            </div>
          </section>

          <section className="reportControlBlock">
            <div className="reportBlockHead">
              <span>03</span>
              <h2>内容模块</h2>
            </div>
            <div className="reportCheckGrid">
              {moduleOptions.map((option) => (
                <label className="reportCheck" key={option.value}>
                  <input
                    checked={form.modules.includes(option.value)}
                    onChange={() => toggleModule(option.value)}
                    type="checkbox"
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="reportControlBlock">
            <div className="reportBlockHead">
              <span>04</span>
              <h2>输出格式</h2>
            </div>
            <div className="formatRow">
              {outputFormatOptions.map((option) => (
                <label className={option.enabled ? "formatPill active" : "formatPill disabled"} key={option.value}>
                  <input
                    checked={form.outputFormat === option.value}
                    disabled={!option.enabled}
                    onChange={() => updateField("outputFormat", option.value)}
                    type="radio"
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </section>

          {error ? <p className="errorText">{error}</p> : null}

          <button className="btn btnPrimary reportGenerateButton" disabled={isGenerating} type="submit">
            {isGenerating ? <RefreshCcw aria-hidden="true" size={16} /> : <Wand2 aria-hidden="true" size={16} />}
            {isGenerating ? "生成中" : "生成报告"}
          </button>
        </form>

        <aside className="reportSidePanel">
          <section className="panel reportSummaryPanel">
            <p className="eyebrow">Current Scope</p>
            <h2>{activeIndustry.label}</h2>
            <p>{activeIndustry.description}</p>
            <div className="tagRow">
              <span>{timeRangeOptions.find((item) => item.value === form.timeRange)?.label}</span>
              <span>{reportTypeOptions.find((item) => item.value === form.reportType)?.label}</span>
              <span>{styleOptions.find((item) => item.value === form.style)?.label}</span>
            </div>
            <button className="secondaryButton reportRetryButton" disabled={isRetrying} onClick={retryFailedSources} type="button">
              <RefreshCcw aria-hidden="true" size={15} />
              {isRetrying ? "重试中" : "重试异常信源"}
            </button>
            {retryResult ? (
              <p className="mutedNote">
                已重试 {retryResult.attemptedCount} 个，成功 {retryResult.successCount} 个，失败{" "}
                {retryResult.failedCount} 个，跳过 {retryResult.skippedCount} 个。
              </p>
            ) : null}
            {retryResult?.errors.length ? <p className="errorText">{retryResult.errors[0]}</p> : null}
            {retryError ? <p className="errorText">{retryError}</p> : null}
          </section>

          <section className="panel reportSummaryPanel">
            <p className="eyebrow">Archives</p>
            <h2>历史日报</h2>
            <div className="reportArchiveLinks">
              {industryOptions
                .filter((item) => item.value !== "ai")
                .map((item) => (
                  <Link href={`/industry/${item.value}`} key={item.value}>
                    {item.label}
                  </Link>
                ))}
            </div>
          </section>
        </aside>
      </div>

      <section className="panel reportResultPanel">
        <div className="reportResultHead">
          <div>
            <p className="eyebrow">Markdown Preview</p>
            <h2>{result?.title ?? "等待生成"}</h2>
          </div>
          {result ? (
            <a
              className="buttonLink"
              href={`/api/briefs/exports/${result.exportId}/download`}
            >
              <Download aria-hidden="true" size={16} />
              下载 Markdown
            </a>
          ) : null}
        </div>
        {result ? (
          <>
            <div className="reportMetaLine">
              <span>{result.eventClusterIds.length} 条事件</span>
              <span>{result.aiStatus === "success" ? "AI 生成" : "生成失败"}</span>
              {result.aiError ? <span>{result.aiError}</span> : null}
            </div>
            <pre className="markdownPreview reportMarkdown">{result.markdown}</pre>
          </>
        ) : (
          <div className="emptyState reportEmptyState">
            <FileText aria-hidden="true" size={22} />
            <h2>还没有生成报告</h2>
            <p>点击生成后，这里会展示 Markdown 内容，并提供下载入口。</p>
          </div>
        )}
      </section>
    </section>
  );
}
