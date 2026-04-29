import { revalidatePath } from "next/cache";
import {
  Source,
  deleteJson,
  fetchJson,
  formatDateTime,
  patchJsonBody,
  postJson,
  postJsonBody,
} from "../../lib/api";

export const dynamic = "force-dynamic";

type SourceCard = {
  type: string;
  title: string;
  summary: string;
  fields: SourceField[];
  disabledReason?: string;
  presets?: string[];
};

type SourceField =
  | {
      name: string;
      label: string;
      type: "text" | "url" | "number";
      defaultValue?: string | number;
      placeholder?: string;
      min?: number;
      max?: number;
      required?: boolean;
    }
  | {
      name: string;
      label: string;
      type: "select";
      defaultValue?: string;
      options: Array<{ label: string; value: string }>;
    };

const sourceCards: SourceCard[] = [
  {
    type: "rss",
    title: "RSS",
    summary: "订阅博客、公告、媒体和研究机构的公开 RSS/Atom/JSON Feed。",
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "OpenAI Blog", required: true },
      { name: "url", label: "Feed URL", type: "url", placeholder: "https://example.com/feed.xml", required: true },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 60, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 1, min: 1, max: 10 },
    ],
  },
  {
    type: "webpage",
    title: "公开网页监控",
    summary: "监控公开页面或指定 CSS 区域，适合公告页、更新页和公开热榜页。",
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "产品更新页", required: true },
      { name: "url", label: "页面 URL", type: "url", placeholder: "https://example.com/changelog", required: true },
      { name: "cssSelector", label: "CSS Selector", type: "text", placeholder: "main 或 .content" },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 120, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 1, min: 1, max: 10 },
    ],
  },
  {
    type: "hacker_news",
    title: "Hacker News",
    summary: "抓取 HN 官方 API 的热门、新发、精选和 Show HN 列表。",
    presets: ["top", "new", "best", "show"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "HN top", required: true },
      {
        name: "listType",
        label: "列表",
        type: "select",
        defaultValue: "top",
        options: [
          { label: "Top", value: "top" },
          { label: "New", value: "new" },
          { label: "Best", value: "best" },
          { label: "Show HN", value: "show" },
        ],
      },
      { name: "limit", label: "数量", type: "number", defaultValue: 30, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 60, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "github_repo",
    title: "GitHub Repo Watch",
    summary: "跟踪指定仓库的 stars、forks、open issues 等基础指标。",
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "vercel/next.js", required: true },
      { name: "url", label: "仓库 URL 或 owner/repo", type: "text", placeholder: "https://github.com/vercel/next.js", required: true },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 180, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "github_release",
    title: "GitHub Release Watch",
    summary: "跟踪指定仓库的新 release 和 release assets 下载量。",
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "Next.js releases", required: true },
      { name: "url", label: "仓库 URL 或 owner/repo", type: "text", placeholder: "vercel/next.js", required: true },
      { name: "limit", label: "Release 数", type: "number", defaultValue: 10, min: 1, max: 50 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 180, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "hotlist",
    title: "热榜信源",
    summary: "规划接入 GitHub Trending、Hugging Face Models、Hugging Face Papers、Product Hunt 等热榜。",
    disabledReason: "等待 hotlist Connector 落地后启用创建；当前可先用公开网页监控接入单个热榜页面。",
    presets: ["GitHub Trending", "HF Models", "HF Papers", "Product Hunt"],
    fields: [],
  },
  {
    type: "youtube_placeholder",
    title: "YouTube Placeholder",
    summary: "仅保留 Connector 占位，不执行真实 API 请求或网页抓取。",
    disabledReason: "v0.1 范围禁止 YouTube 真实抓取。",
    fields: [],
  },
];

async function createSourceAction(formData: FormData) {
  "use server";
  const type = stringValue(formData, "sourceType");
  if (type === "hotlist" || type === "youtube_placeholder") {
    return;
  }

  await postJsonBody<Source>("/api/sources", {
    type,
    name: stringValue(formData, "name", defaultSourceName(type)),
    url: optionalStringValue(formData, "url"),
    enabled: true,
    weight: numberValue(formData, "weight", 1),
    pollIntervalMinutes: numberValue(formData, "pollIntervalMinutes", 60),
    configJson: configJsonFor(type, formData),
  });
  revalidatePath("/sources");
}

async function toggleSourceAction(formData: FormData) {
  "use server";
  const sourceId = stringValue(formData, "sourceId");
  await patchJsonBody<Source>(`/api/sources/${sourceId}`, {
    enabled: stringValue(formData, "enabled") === "true",
  });
  revalidatePath("/sources");
}

async function refreshSourceAction(formData: FormData) {
  "use server";
  const sourceId = stringValue(formData, "sourceId");
  await postJson(`/api/sources/${sourceId}/refresh`);
  revalidatePath("/sources");
}

async function deleteSourceAction(formData: FormData) {
  "use server";
  if (formData.get("confirmDelete") !== "on") {
    return;
  }
  const sourceId = stringValue(formData, "sourceId");
  await deleteJson(`/api/sources/${sourceId}`);
  revalidatePath("/sources");
}

export default async function SourcesPage() {
  let sources: Source[] = [];
  let error: string | null = null;

  try {
    sources = await fetchJson<Source[]>("/api/sources");
  } catch (caught) {
    error = caught instanceof Error ? caught.message : "无法读取信源";
  }

  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Sources</p>
        <h1>信源管理</h1>
        <p>按信源类型配置本地抓取入口，刷新结果统一进入 RawItem、FetchRun、Evidence 和事件聚类链路。</p>
      </header>

      {error ? <StatePanel title="无法读取信源" detail={error} /> : null}

      {!error ? (
        <div className="sourceGrid">
          {sourceCards.map((card) => (
            <SourceCardPanel
              card={card}
              key={card.type}
              sources={sources.filter((source) => source.type === card.type)}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

function SourceCardPanel({ card, sources }: { card: SourceCard; sources: Source[] }) {
  return (
    <article className="panel sourcePanel">
      <div className="sourcePanelHeader">
        <div>
          <p className="eyebrow">{card.type}</p>
          <h2>{card.title}</h2>
        </div>
        <span className={sources.some((source) => source.enabled) ? "statusBadge" : "statusBadge off"}>
          {sources.length} 个配置
        </span>
      </div>

      <p>{card.summary}</p>

      {card.presets ? (
        <div className="tagRow">
          {card.presets.map((preset) => (
            <span key={preset}>{preset}</span>
          ))}
        </div>
      ) : null}

      {card.disabledReason ? (
        <p className="mutedNote">{card.disabledReason}</p>
      ) : (
        <form action={createSourceAction} className="sourceForm">
          <input name="sourceType" type="hidden" value={card.type} />
          <div className="sourceFormGrid">
            {card.fields.map((field) => (
              <SourceFieldControl field={field} key={field.name} />
            ))}
          </div>
          <button type="submit">新增信源</button>
        </form>
      )}

      <div className="sourceInstanceList">
        {sources.length === 0 ? (
          <p className="mutedNote">暂无已配置实例。</p>
        ) : (
          sources.map((source) => <SourceInstance key={source.id} source={source} />)
        )}
      </div>
    </article>
  );
}

function SourceFieldControl({ field }: { field: SourceField }) {
  return (
    <label className="fieldStack">
      {field.label}
      {field.type === "select" ? (
        <select name={field.name} defaultValue={field.defaultValue}>
          {field.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          defaultValue={field.defaultValue}
          max={field.max}
          min={field.min}
          name={field.name}
          placeholder={field.placeholder}
          required={field.required}
          type={field.type}
        />
      )}
    </label>
  );
}

function SourceInstance({ source }: { source: Source }) {
  const supportsRuntimeActions = source.type !== "youtube_placeholder" && source.type !== "hotlist";

  return (
    <div className="sourceInstance">
      <div className="sourceInstanceMain">
        <div className="sourceInstanceTitle">
          <strong>{source.name}</strong>
          <span className={source.enabled ? "statusBadge" : "statusBadge off"}>
            {source.enabled ? "启用" : "停用"}
          </span>
        </div>
        <small>{sourceConfigSummary(source)}</small>
        <small>
          刷新 {source.pollIntervalMinutes} 分钟 / 权重 {source.weight} / 最近抓取{" "}
          {formatDateTime(source.lastFetchedAt)}
        </small>
        {source.lastError ? <small className="errorText">{source.lastError}</small> : null}
      </div>

      <div className="sourceActions">
        {supportsRuntimeActions ? (
          <>
            <form action={toggleSourceAction}>
              <input name="sourceId" type="hidden" value={source.id} />
              <input name="enabled" type="hidden" value={source.enabled ? "false" : "true"} />
              <button className="secondaryButton" type="submit">
                {source.enabled ? "停用" : "启用"}
              </button>
            </form>
            <form action={refreshSourceAction}>
              <input name="sourceId" type="hidden" value={source.id} />
              <button className="secondaryButton" type="submit">
                立即刷新
              </button>
            </form>
          </>
        ) : (
          <span className="mutedNote">当前不可抓取</span>
        )}
        <form action={deleteSourceAction} className="deleteSourceForm">
          <input name="sourceId" type="hidden" value={source.id} />
          <label className="confirmLine">
            <input name="confirmDelete" required type="checkbox" />
            确认删除
          </label>
          <button className="dangerButton" type="submit">
            删除
          </button>
        </form>
      </div>
    </div>
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

function sourceConfigSummary(source: Source): string {
  if (source.type === "hacker_news") {
    return `列表 ${stringFromConfig(source, "listType", "top")} / 数量 ${stringFromConfig(source, "limit", "30")}`;
  }
  if (source.type === "webpage") {
    return `${source.url || "未配置 URL"} / ${stringFromConfig(source, "cssSelector", "全文")}`;
  }
  if (source.type === "github_release") {
    return `${source.url || "未配置仓库"} / Release 数 ${stringFromConfig(source, "limit", "10")}`;
  }
  if (source.type === "hotlist") {
    return `${stringFromConfig(source, "provider", "未配置 provider")} / ${stringFromConfig(source, "period", "daily")}`;
  }
  return source.url || "未配置 URL";
}

function stringFromConfig(source: Source, key: string, fallback: string): string {
  const value = source.configJson[key];
  return value === undefined || value === null || value === "" ? fallback : String(value);
}

function configJsonFor(type: string, formData: FormData): Record<string, unknown> {
  if (type === "webpage") {
    return {
      cssSelector: optionalStringValue(formData, "cssSelector"),
      extractionMode: "css_selector",
    };
  }
  if (type === "hacker_news") {
    return {
      listType: stringValue(formData, "listType", "top"),
      limit: numberValue(formData, "limit", 30),
    };
  }
  if (type === "github_release") {
    return {
      limit: numberValue(formData, "limit", 10),
    };
  }
  return {};
}

function defaultSourceName(type: string): string {
  return sourceCards.find((card) => card.type === type)?.title || "Source";
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
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}
