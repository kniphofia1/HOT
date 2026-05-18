import Link from "next/link";
import { ExternalLink } from "lucide-react";
import type { TimelineItem, TimelinePage } from "../lib/api";

export type FeedSearchParams = {
  category?: string;
  industry?: string;
  sourceKind?: string;
  hours?: string;
  q?: string;
  page?: string;
};

const categories = [
  { label: "全部", value: "" },
  { label: "模型", value: "ai-models" },
  { label: "产品", value: "ai-products" },
  { label: "行业", value: "industry" },
  { label: "论文", value: "paper" },
  { label: "技巧", value: "tip" },
];

const sourceKinds = [
  { label: "全部来源", value: "" },
  { label: "媒体/RSS", value: "news" },
  { label: "社交", value: "social" },
  { label: "一手源", value: "first_party" },
];

const industries = [
  { label: "全部", value: "" },
  { label: "AI", value: "ai" },
  { label: "半导体", value: "semiconductor" },
  { label: "具身智能", value: "embodied_ai" },
  { label: "新能源", value: "energy" },
  { label: "技术", value: "technology" },
  { label: "产品", value: "products" },
];

const timeRanges = [
  { label: "12小时", value: "12" },
  { label: "24小时", value: "24" },
  { label: "全部时间", value: "" },
];

export function FeedPage({
  feed,
  params,
  title,
  subtitle,
  basePath,
  showCategoryFilter = false,
  showSourceFilter = false,
  showIndustryFilter = false,
  showTimeFilter = false,
}: {
  feed: TimelinePage;
  params: FeedSearchParams;
  title: string;
  subtitle: string;
  basePath: string;
  showCategoryFilter?: boolean;
  showSourceFilter?: boolean;
  showIndustryFilter?: boolean;
  showTimeFilter?: boolean;
}) {
  const grouped = groupByDay(feed.items);
  const page = Number(params.page || "1");
  const totalPages = Math.max(1, Math.ceil(feed.total / feed.take));

  return (
    <div className="page pageTheme pageThemeFeed">
      <section className="card pageHeader pageHeaderFeed pageHeaderCompact">
        <div className="headerRow">
          <div>
            <h1 className="title pageTitle">{title}</h1>
            <p className="muted pageSubtitle">{subtitle}</p>
          </div>
        </div>
        <div className="divider pageDivider" />
        <div className="pageHeaderBody">
          <div className="feedToolbarRow">
            {showCategoryFilter ? <SegmentedControl basePath={basePath} params={params} /> : null}
            {showIndustryFilter ? <IndustryControl basePath={basePath} params={params} /> : null}
            {showTimeFilter ? <TimeRangeControl basePath={basePath} params={params} /> : null}
            {showSourceFilter ? <SourceKindControl basePath={basePath} params={params} /> : null}
            <form className="filterForm feedFilterForm" action={basePath} method="get">
              {showCategoryFilter && params.category ? <input name="category" type="hidden" value={params.category} /> : null}
              {params.industry ? <input name="industry" type="hidden" value={params.industry} /> : null}
              {params.sourceKind ? <input name="sourceKind" type="hidden" value={params.sourceKind} /> : null}
              {params.hours ? <input name="hours" type="hidden" value={params.hours} /> : null}
              <div className="filterToolbar feedFilterSearchRow">
                <input
                  className="field fieldGrow feedFilterSearchInput"
                  defaultValue={params.q ?? ""}
                  name="q"
                  placeholder="搜索标题/摘要..."
                />
                <button className="btn btnPrimary btnSm filterSubmit feedFilterSubmit" type="submit">
                  搜索
                </button>
              </div>
              <input name="page" type="hidden" value="1" />
            </form>
          </div>
        </div>
      </section>

      {feed.items.length === 0 ? (
        <section className="emptyState">
          <h2>暂无内容</h2>
          <p>完成信源刷新、聚类和评分后，内容会进入这里。</p>
        </section>
      ) : (
        <section className="timeline">
          {grouped.map((group) => (
            <div className="timelineDay" key={group.day}>
              <div className="timelineDayHead">
                <div className="timelineDate">{formatDayLabel(group.day)}</div>
                <div aria-hidden="true" />
              </div>
              <div className="timelineDayItems">
                {group.items.map((item) => (
                  <TimelineCard item={item} key={item.id} />
                ))}
              </div>
            </div>
          ))}
        </section>
      )}

      {totalPages > 1 ? (
        <nav className="feedPagination" aria-label="分页">
          <PageLink basePath={basePath} disabled={page <= 1} label="上一页" page={page - 1} params={params} />
          <span>
            {page} / {totalPages}
          </span>
          <PageLink basePath={basePath} disabled={page >= totalPages} label="下一页" page={page + 1} params={params} />
        </nav>
      ) : null}
    </div>
  );
}

function SegmentedControl({ basePath, params }: { basePath: string; params: FeedSearchParams }) {
  return (
    <div className="segmented" aria-label="分类筛选">
      {categories.map((category) => (
        <Link
          aria-current={(params.category || "") === category.value ? "page" : undefined}
          className={(params.category || "") === category.value ? "segItem segItemActive" : "segItem"}
          href={hrefWith(basePath, { ...params, category: category.value, page: "1" })}
          key={category.label}
        >
          {category.label}
        </Link>
      ))}
    </div>
  );
}

function TimeRangeControl({ basePath, params }: { basePath: string; params: FeedSearchParams }) {
  return (
    <div className="segmented timeSegmented" aria-label="时间范围筛选">
      {timeRanges.map((range) => (
        <Link
          className={(params.hours || "") === range.value ? "segItem segItemActive" : "segItem"}
          href={hrefWith(basePath, { ...params, hours: range.value, page: "1" })}
          key={range.label}
        >
          {range.label}
        </Link>
      ))}
    </div>
  );
}

function SourceKindControl({ basePath, params }: { basePath: string; params: FeedSearchParams }) {
  return (
    <div className="segmented sourceSegmented" aria-label="来源筛选">
      {sourceKinds.map((kind) => (
        <Link
          className={(params.sourceKind || "") === kind.value ? "segItem segItemActive" : "segItem"}
          href={hrefWith(basePath, { ...params, sourceKind: kind.value, page: "1" })}
          key={kind.label}
        >
          {kind.label}
        </Link>
      ))}
    </div>
  );
}

function IndustryControl({ basePath, params }: { basePath: string; params: FeedSearchParams }) {
  return (
    <div className="segmented industrySegmented" aria-label="行业筛选">
      {industries.map((industry) => (
        <Link
          className={(params.industry || "") === industry.value ? "segItem segItemActive" : "segItem"}
          href={hrefWith(basePath, { ...params, industry: industry.value, page: "1" })}
          key={industry.label}
        >
          {industry.label}
        </Link>
      ))}
    </div>
  );
}

function TimelineCard({ item }: { item: TimelineItem }) {
  const timeValue = item.publishedAt || item.displayedAt || item.seenAt;
  const industryLabels = Array.isArray(item.industryLabels) ? item.industryLabels : [];
  const relatedIndustryLabels = Array.isArray(item.relatedIndustryLabels) ? item.relatedIndustryLabels : [];
  const tags = Array.isArray(item.tags) ? item.tags : [];
  const mediaUrls = Array.isArray(item.mediaUrls) ? item.mediaUrls : [];
  const sourceName = item.sourceName || "未知来源";
  return (
    <div className={item.selected ? "timelineItem timelineItemSelected" : "timelineItem"}>
      <time className="timelineTime" dateTime={timeValue ?? undefined}>
        {formatTime(timeValue)}
        {item.timeBasis !== "source_published" ? <span className="timelineTimeBasis">发现</span> : null}
      </time>
      <div className="timelineRail" aria-hidden="true">
        <span className="timelineDot" />
      </div>
      <article className="timelineCard">
        <div className="timelineCardHead">
          <div className="timelineHeadLeft">
            {item.avatarUrl ? (
              <img alt="" className="ucAvatar" height={20} src={item.avatarUrl} width={20} />
            ) : (
              <span className="ucAvatar avatarFallback" aria-hidden="true">
                {avatarInitial(sourceName)}
              </span>
            )}
            <span className="timelineSource">{sourceName}</span>
            {item.author ? <span className="ucHandle">@{item.author}</span> : null}
          </div>
          <div className="timelineHeadRight">
            {item.selected ? <span className="timelineSelectedBadge" title="编辑精选">精选</span> : null}
            <span className={item.score >= 70 ? "timelineScore scoreHigh" : "timelineScore scoreMid"} title="AI 推荐分">
              {item.score}
            </span>
          </div>
        </div>

        {item.url ? (
          <a className="timelineTitle" href={item.url} rel="noopener noreferrer" target="_blank">
            {item.displayTitle}
          </a>
        ) : (
          <Link className="timelineTitle" href={`/events/${item.id}`}>
            {item.displayTitle}
          </Link>
        )}
        <p className="timelineSummary">{item.displaySummary || "暂无摘要"}</p>

        {mediaUrls.length > 0 ? (
          <div className={mediaUrls.length === 1 ? "feedMedia feedMediaSingle" : "feedMedia feedMediaGrid"}>
            {mediaUrls.slice(0, 4).map((url, index) => (
              <a className="feedMediaCell" href={url} key={url} rel="noopener noreferrer" target="_blank">
                <img alt="" className="feedMediaImg" loading="lazy" src={url} />
                {index === 3 && mediaUrls.length > 4 ? <span>+{mediaUrls.length - 4}</span> : null}
              </a>
            ))}
          </div>
        ) : null}

        <div className="timelineTags">
          {industryLabels.map((label) => (
            <span className="tag tagStatic" key={`industry-${label}`}>
              {label}
            </span>
          ))}
          {relatedIndustryLabels.map((label) => (
            <span className="tag tagStatic tagMuted" key={`related-industry-${label}`}>
              {label}
            </span>
          ))}
          {tags.map((tag) => (
            <span className="tag tagStatic" key={tag}>
              {tag}
            </span>
          ))}
        </div>
        <hr className="timelineDivider" />
        <div className="timelineReason">
          <span className="timelineReasonLabel">推荐理由：</span>
          {item.reason}
        </div>
        <Link className="timelineDetailLink" href={`/events/${item.id}`}>
          {item.evidenceCount} 条证据
          <ExternalLink aria-hidden="true" size={13} />
        </Link>
      </article>
    </div>
  );
}

function PageLink({
  basePath,
  disabled,
  label,
  page,
  params,
}: {
  basePath: string;
  disabled: boolean;
  label: string;
  page: number;
  params: FeedSearchParams;
}) {
  if (disabled) {
    return <span className="feedPaginationDisabled">{label}</span>;
  }
  return (
    <Link className="feedPaginationLink" href={hrefWith(basePath, { ...params, page: String(page) })}>
      {label}
    </Link>
  );
}

function groupByDay(items: TimelineItem[]): Array<{ day: string; items: TimelineItem[] }> {
  const groups = new Map<string, TimelineItem[]>();
  for (const item of items) {
    const key = dayKey(item.publishedAt || item.displayedAt || item.seenAt);
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return Array.from(groups.entries()).map(([day, groupItems]) => ({ day, items: groupItems }));
}

function dayKey(value: string | null): string {
  if (!value) {
    return "unknown";
  }
  return new Date(value).toISOString().slice(0, 10);
}

function formatDayLabel(value: string): string {
  if (value === "unknown") {
    return "未记录";
  }
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(date);
}

function formatTime(value: string | null): string {
  if (!value) {
    return "--:--";
  }
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value));
}

function avatarInitial(value: string): string {
  return value.trim().slice(0, 1).toUpperCase() || "A";
}

function hrefWith(basePath: string, params: FeedSearchParams): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) {
      query.set(key, value);
    }
  }
  const suffix = query.toString();
  return suffix ? `${basePath}?${suffix}` : basePath;
}
