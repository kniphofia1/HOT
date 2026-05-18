import { revalidatePath } from "next/cache";
import {
  Source,
  RefreshRun,
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
      type: "text" | "url" | "number" | "textarea";
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

const disabledSourceTypes = new Set(["restricted_social", "youtube_placeholder", "manual_link"]);

const sourceCards: SourceCard[] = [
  {
    type: "rss",
    title: "RSS",
    summary: "订阅博客、公告、媒体和研究机构的公开 RSS、Atom 或 JSON Feed。",
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
    summary: "监控公开页面或指定 CSS 区域，适合公告页、更新页和公开榜单页。",
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
    type: "sec_edgar_filings",
    title: "SEC EDGAR Filings",
    summary: "通过 SEC 官方公开 submissions API 跟踪公司 10-K、10-Q、8-K 等公告。",
    presets: ["Official API", "Filings", "10-K/10-Q/8-K"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "SEC AI infrastructure filings", required: true },
      { name: "url", label: "入口 URL", type: "url", defaultValue: "https://www.sec.gov/search-filings" },
      {
        name: "companiesJson",
        label: "Companies JSON",
        type: "textarea",
        placeholder: "[{\"ticker\":\"NVDA\",\"name\":\"NVIDIA\",\"cik\":\"1045810\"}]",
        required: true,
      },
      { name: "forms", label: "Forms", type: "text", defaultValue: "10-K,10-Q,8-K" },
      { name: "limit", label: "数量", type: "number", defaultValue: 30, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 360, min: 30 },
      { name: "weight", label: "权重", type: "number", defaultValue: 4, min: 1, max: 10 },
    ],
  },
  {
    type: "reddit_subreddit",
    title: "Reddit Subreddit",
    summary: "按 subreddit 抓取 hot、new、top、rising 或站内搜索结果，记录分数和评论数。",
    presets: ["hot", "new", "top", "rising", "search"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "Reddit r/MachineLearning", required: true },
      { name: "subreddit", label: "Subreddit", type: "text", placeholder: "MachineLearning", required: true },
      {
        name: "sort",
        label: "列表",
        type: "select",
        defaultValue: "hot",
        options: [
          { label: "Hot", value: "hot" },
          { label: "New", value: "new" },
          { label: "Top", value: "top" },
          { label: "Rising", value: "rising" },
          { label: "Search", value: "search" },
        ],
      },
      {
        name: "timeRange",
        label: "时间范围",
        type: "select",
        defaultValue: "day",
        options: [
          { label: "Hour", value: "hour" },
          { label: "Day", value: "day" },
          { label: "Week", value: "week" },
          { label: "Month", value: "month" },
          { label: "Year", value: "year" },
          { label: "All", value: "all" },
        ],
      },
      { name: "query", label: "搜索词", type: "text", placeholder: "仅 search 需要" },
      { name: "limit", label: "数量", type: "number", defaultValue: 25, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 60, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "bluesky_search",
    title: "Bluesky Search",
    summary: "按关键词抓取 Bluesky 帖子；部分环境下搜索端点可能要求鉴权，失败时优先使用 Author Feed。",
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "Bluesky AI search", required: true },
      { name: "query", label: "关键词", type: "text", placeholder: "open source AI", required: true },
      { name: "actor", label: "作者 handle", type: "text", placeholder: "可选，例如 bsky.app" },
      { name: "limit", label: "数量", type: "number", defaultValue: 25, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 60, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "bluesky_actor_feed",
    title: "Bluesky Author Feed",
    summary: "抓取指定 Bluesky 账号的公开时间线，适合跟踪官方账号、研究员和机构账号。",
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "Bluesky official", required: true },
      { name: "actor", label: "账号 handle", type: "text", placeholder: "bsky.app", required: true },
      { name: "limit", label: "数量", type: "number", defaultValue: 25, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 60, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "mastodon_timeline",
    title: "Mastodon Timeline",
    summary: "抓取指定 Mastodon 实例的公开时间线或标签时间线，记录回复、转发和收藏指标。",
    presets: ["public", "tag"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "Mastodon AI tag", required: true },
      { name: "instanceUrl", label: "实例 URL", type: "url", placeholder: "https://mastodon.social", required: true },
      {
        name: "mode",
        label: "模式",
        type: "select",
        defaultValue: "public",
        options: [
          { label: "Public", value: "public" },
          { label: "Tag", value: "tag" },
        ],
      },
      { name: "tag", label: "标签", type: "text", placeholder: "仅 tag 需要，例如 ai" },
      { name: "limit", label: "数量", type: "number", defaultValue: 25, min: 1, max: 40 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 60, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "x_recent_search",
    title: "X Recent Search",
    summary: "通过 X 官方 recent search API 抓取公开讨论，需要付费 API 权限和 bearer token 环境变量。",
    presets: ["Official API", "Bearer Token", "Metrics"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "X AI search", required: true },
      { name: "query", label: "搜索语句", type: "text", placeholder: "open source AI lang:en", required: true },
      { name: "bearerTokenEnv", label: "Token 环境变量", type: "text", defaultValue: "X_BEARER_TOKEN" },
      { name: "limit", label: "数量", type: "number", defaultValue: 25, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 60, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 3, min: 1, max: 10 },
    ],
  },
  {
    type: "youtube_channel",
    title: "YouTube Channel",
    summary: "通过 YouTube Data API 跟踪频道或关键词视频，不做网页抓取；需要 API key 和配额。",
    presets: ["Data API", "API Key", "Quota"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "YouTube AI channel", required: true },
      { name: "channelId", label: "Channel ID", type: "text", placeholder: "UC..." },
      { name: "query", label: "关键词", type: "text", placeholder: "可选，频道内或全站关键词" },
      { name: "apiKeyEnv", label: "API Key 环境变量", type: "text", defaultValue: "YOUTUBE_API_KEY" },
      { name: "limit", label: "数量", type: "number", defaultValue: 10, min: 1, max: 50 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 180, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "linkedin_posts",
    title: "LinkedIn Posts",
    summary: "通过 LinkedIn 官方 Posts API 跟踪授权主体内容，通常需要平台审核和组织授权。",
    presets: ["Official API", "Access Token", "Reviewed"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "LinkedIn company posts", required: true },
      { name: "authorUrn", label: "Author URN", type: "text", placeholder: "urn:li:organization:123", required: true },
      { name: "accessTokenEnv", label: "Token 环境变量", type: "text", defaultValue: "LINKEDIN_ACCESS_TOKEN" },
      { name: "version", label: "API Version", type: "text", defaultValue: "202602" },
      { name: "limit", label: "数量", type: "number", defaultValue: 20, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 240, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "tiktok_research",
    title: "TikTok Research API",
    summary: "通过 TikTok Research API 查询公开研究数据，需要官方授权；查询体按官方 JSON 填写。",
    presets: ["Research API", "Access Token", "Reviewed"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "TikTok AI research", required: true },
      { name: "queryJson", label: "Query JSON", type: "textarea", placeholder: "{\"query\":{\"and\":[{\"operation\":\"EQ\",\"field_name\":\"keyword\",\"field_values\":[\"ai\"]}]}}" },
      { name: "accessTokenEnv", label: "Token 环境变量", type: "text", defaultValue: "TIKTOK_RESEARCH_ACCESS_TOKEN" },
      { name: "limit", label: "数量", type: "number", defaultValue: 20, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 240, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "telegram_updates",
    title: "Telegram Bot Updates",
    summary: "读取 bot 已加入并授权的频道或群更新，不处理登录态或私有页面。",
    presets: ["Bot API", "Authorized Channel"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "Telegram channel", required: true },
      { name: "chatId", label: "Chat ID", type: "text", placeholder: "可选，用于过滤指定频道/群" },
      { name: "botTokenEnv", label: "Bot Token 环境变量", type: "text", defaultValue: "TELEGRAM_BOT_TOKEN" },
      { name: "limit", label: "数量", type: "number", defaultValue: 50, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 30, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "discord_channel",
    title: "Discord Channel",
    summary: "读取 bot 已授权访问的指定频道消息，适合跟踪社区公告和项目讨论。",
    presets: ["Bot API", "Authorized Channel"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "Discord announcements", required: true },
      { name: "channelId", label: "Channel ID", type: "text", required: true },
      { name: "guildId", label: "Guild ID", type: "text", placeholder: "可选，用于生成消息链接" },
      { name: "botTokenEnv", label: "Bot Token 环境变量", type: "text", defaultValue: "DISCORD_BOT_TOKEN" },
      { name: "limit", label: "数量", type: "number", defaultValue: 50, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 30, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "slack_channel",
    title: "Slack Channel",
    summary: "读取 workspace 已授权范围内的 conversation history，用于团队或社区信号追踪。",
    presets: ["Workspace API", "OAuth Token"],
    fields: [
      { name: "name", label: "名称", type: "text", placeholder: "Slack channel", required: true },
      { name: "channelId", label: "Channel ID", type: "text", required: true },
      { name: "botTokenEnv", label: "Bot Token 环境变量", type: "text", defaultValue: "SLACK_BOT_TOKEN" },
      { name: "limit", label: "数量", type: "number", defaultValue: 50, min: 1, max: 100 },
      { name: "pollIntervalMinutes", label: "刷新分钟", type: "number", defaultValue: 30, min: 5 },
      { name: "weight", label: "权重", type: "number", defaultValue: 2, min: 1, max: 10 },
    ],
  },
  {
    type: "restricted_social",
    title: "受限社交平台",
    summary: "X、YouTube、Instagram/Facebook、TikTok 和国内平台需要单独的 API、成本与合规方案。",
    disabledReason: "当前不会抓取需要登录态、Cookie、验证码、私有页面或反爬绕过的平台。后续必须先补充 ADR 和 Connector 合规边界。",
    presets: ["X deferred", "YouTube placeholder", "国内平台 deferred"],
    fields: [],
  },
  {
    type: "manual_link",
    title: "人工链接补录",
    summary: "无法自动接入的平台内容通过信源市场补录，补录内容仍会进入 RawItem 和事件候选链路。",
    disabledReason: "人工补录不执行抓取任务，可在信源市场新增链接证据。",
    presets: ["Manual Evidence", "RawItem"],
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
  if (disabledSourceTypes.has(type)) {
    return;
  }

  await postJsonBody<Source>("/api/sources", {
    type,
    name: stringValue(formData, "name", defaultSourceName(type)),
    url: optionalStringValue(formData, "url") ?? optionalStringValue(formData, "instanceUrl"),
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
  await postJson<RefreshRun>(`/api/sources/${sourceId}/refresh`);
  revalidatePath("/");
  revalidatePath("/sources");
  revalidatePath("/runs");
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
      ) : field.type === "textarea" ? (
        <textarea
          defaultValue={field.defaultValue}
          name={field.name}
          placeholder={field.placeholder}
          required={field.required}
        />
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
  const supportsRuntimeActions = !disabledSourceTypes.has(source.type);

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
          刷新 {source.pollIntervalMinutes} 分钟 / 权重 {source.weight} / 最新内容{" "}
          {formatDateTime(source.latestPublishedAt)}
        </small>
        <small>
          最近抓取 {formatDateTime(source.lastFetchedAt)}
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
  if (source.type === "sec_edgar_filings") {
    const companies = source.configJson.companies;
    const companyCount = Array.isArray(companies) ? companies.length : 0;
    return `SEC EDGAR / ${companyCount} 家公司 / Forms ${stringFromConfig(source, "forms", "10-K,10-Q,8-K")}`;
  }
  if (source.type === "reddit_subreddit") {
    return `r/${stringFromConfig(source, "subreddit", "未配置")} / ${stringFromConfig(
      source,
      "sort",
      "hot",
    )} / 数量 ${stringFromConfig(source, "limit", "25")}`;
  }
  if (source.type === "bluesky_search") {
    return `关键词 ${stringFromConfig(source, "query", "未配置")} / 作者 ${stringFromConfig(
      source,
      "actor",
      "不限",
    )} / 数量 ${stringFromConfig(source, "limit", "25")}`;
  }
  if (source.type === "bluesky_actor_feed") {
    return `账号 @${stringFromConfig(source, "actor", "未配置")} / 数量 ${stringFromConfig(source, "limit", "25")}`;
  }
  if (source.type === "mastodon_timeline") {
    const mode = stringFromConfig(source, "mode", "public");
    const label = mode === "tag" ? `#${stringFromConfig(source, "tag", "未配置")}` : "public";
    return `${stringFromConfig(source, "instanceUrl", source.url || "未配置实例")} / ${label} / 数量 ${stringFromConfig(
      source,
      "limit",
      "25",
    )}`;
  }
  if (source.type === "x_recent_search") {
    return `Query ${stringFromConfig(source, "query", "未配置")} / Env ${stringFromConfig(
      source,
      "bearerTokenEnv",
      "X_BEARER_TOKEN",
    )} / 数量 ${stringFromConfig(source, "limit", "25")}`;
  }
  if (source.type === "youtube_channel") {
    return `Channel ${stringFromConfig(source, "channelId", "不限")} / Query ${stringFromConfig(
      source,
      "query",
      "未配置",
    )} / Env ${stringFromConfig(source, "apiKeyEnv", "YOUTUBE_API_KEY")}`;
  }
  if (source.type === "linkedin_posts") {
    return `Author ${stringFromConfig(source, "authorUrn", "未配置")} / Env ${stringFromConfig(
      source,
      "accessTokenEnv",
      "LINKEDIN_ACCESS_TOKEN",
    )}`;
  }
  if (source.type === "tiktok_research") {
    return `Research API / Env ${stringFromConfig(
      source,
      "accessTokenEnv",
      "TIKTOK_RESEARCH_ACCESS_TOKEN",
    )} / 数量 ${stringFromConfig(source, "limit", "20")}`;
  }
  if (source.type === "telegram_updates") {
    return `Chat ${stringFromConfig(source, "chatId", "不过滤")} / Env ${stringFromConfig(
      source,
      "botTokenEnv",
      "TELEGRAM_BOT_TOKEN",
    )}`;
  }
  if (source.type === "discord_channel") {
    return `Channel ${stringFromConfig(source, "channelId", "未配置")} / Guild ${stringFromConfig(
      source,
      "guildId",
      "未配置",
    )} / Env ${stringFromConfig(source, "botTokenEnv", "DISCORD_BOT_TOKEN")}`;
  }
  if (source.type === "slack_channel") {
    return `Channel ${stringFromConfig(source, "channelId", "未配置")} / Env ${stringFromConfig(
      source,
      "botTokenEnv",
      "SLACK_BOT_TOKEN",
    )}`;
  }
  if (source.type === "manual_link") {
    return "人工补录内容，不执行自动刷新";
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
  if (type === "sec_edgar_filings") {
    return {
      companies: jsonArrayValue(formData, "companiesJson"),
      forms: stringValue(formData, "forms", "10-K,10-Q,8-K")
        .split(",")
        .map((form) => form.trim())
        .filter(Boolean),
      limit: numberValue(formData, "limit", 30),
    };
  }
  if (type === "reddit_subreddit") {
    return {
      subreddit: stringValue(formData, "subreddit"),
      sort: stringValue(formData, "sort", "hot"),
      timeRange: stringValue(formData, "timeRange", "day"),
      query: optionalStringValue(formData, "query"),
      limit: numberValue(formData, "limit", 25),
    };
  }
  if (type === "bluesky_search") {
    return {
      query: stringValue(formData, "query"),
      actor: optionalStringValue(formData, "actor"),
      limit: numberValue(formData, "limit", 25),
    };
  }
  if (type === "bluesky_actor_feed") {
    return {
      actor: stringValue(formData, "actor"),
      limit: numberValue(formData, "limit", 25),
    };
  }
  if (type === "mastodon_timeline") {
    return {
      instanceUrl: stringValue(formData, "instanceUrl"),
      mode: stringValue(formData, "mode", "public"),
      tag: optionalStringValue(formData, "tag"),
      limit: numberValue(formData, "limit", 25),
    };
  }
  if (type === "x_recent_search") {
    return {
      query: stringValue(formData, "query"),
      bearerTokenEnv: stringValue(formData, "bearerTokenEnv", "X_BEARER_TOKEN"),
      limit: numberValue(formData, "limit", 25),
    };
  }
  if (type === "youtube_channel") {
    return {
      channelId: optionalStringValue(formData, "channelId"),
      query: optionalStringValue(formData, "query"),
      apiKeyEnv: stringValue(formData, "apiKeyEnv", "YOUTUBE_API_KEY"),
      limit: numberValue(formData, "limit", 10),
    };
  }
  if (type === "linkedin_posts") {
    return {
      authorUrn: stringValue(formData, "authorUrn"),
      accessTokenEnv: stringValue(formData, "accessTokenEnv", "LINKEDIN_ACCESS_TOKEN"),
      version: stringValue(formData, "version", "202602"),
      limit: numberValue(formData, "limit", 20),
    };
  }
  if (type === "tiktok_research") {
    return {
      queryJson: jsonObjectValue(formData, "queryJson"),
      accessTokenEnv: stringValue(formData, "accessTokenEnv", "TIKTOK_RESEARCH_ACCESS_TOKEN"),
      limit: numberValue(formData, "limit", 20),
    };
  }
  if (type === "telegram_updates") {
    return {
      chatId: optionalStringValue(formData, "chatId"),
      botTokenEnv: stringValue(formData, "botTokenEnv", "TELEGRAM_BOT_TOKEN"),
      limit: numberValue(formData, "limit", 50),
    };
  }
  if (type === "discord_channel") {
    return {
      channelId: stringValue(formData, "channelId"),
      guildId: optionalStringValue(formData, "guildId"),
      botTokenEnv: stringValue(formData, "botTokenEnv", "DISCORD_BOT_TOKEN"),
      limit: numberValue(formData, "limit", 50),
    };
  }
  if (type === "slack_channel") {
    return {
      channelId: stringValue(formData, "channelId"),
      botTokenEnv: stringValue(formData, "botTokenEnv", "SLACK_BOT_TOKEN"),
      limit: numberValue(formData, "limit", 50),
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

function jsonObjectValue(formData: FormData, key: string): Record<string, unknown> {
  const value = stringValue(formData, key);
  if (!value) {
    return {};
  }
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function jsonArrayValue(formData: FormData, key: string): unknown[] {
  const value = stringValue(formData, key);
  if (!value) {
    return [];
  }
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function numberValue(formData: FormData, key: string, fallback: number): number {
  const parsed = Number(stringValue(formData, key));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}
