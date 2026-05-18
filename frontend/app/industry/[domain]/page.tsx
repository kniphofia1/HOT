import Link from "next/link";
import { IndustryDigest, fetchJson } from "../../../lib/api";

export const dynamic = "force-dynamic";

type IndustryParams = {
  date?: string;
};

export default async function IndustryDigestPage({
  params,
  searchParams,
}: {
  params: Promise<{ domain: string }>;
  searchParams?: Promise<IndustryParams>;
}) {
  const { domain } = await params;
  const query = (await searchParams)?.date;
  const digest = await fetchJson<IndustryDigest>(
    `/api/public/industries/${encodeURIComponent(domain)}${query ? `?date=${encodeURIComponent(query)}` : ""}`,
  );

  return (
    <div className="dailyPage">
      <aside className="dailyArchive">
        <Link className="dailyLatest" href={`/industry/${digest.domain}`}>
          <strong>最新一期</strong>
          <span>{digest.archive[0]?.date ?? digest.date}</span>
        </Link>
        <div className="dailyMonth">
          <div className="dailyMonthHead">
            <strong>{digest.label}</strong>
            <span>{digest.archive.length}</span>
          </div>
          <div className="dailyArchiveList">
            {digest.archive.map((item) => (
              <Link
                className={item.date === digest.date ? "dailyArchiveItem active" : "dailyArchiveItem"}
                href={`/industry/${digest.domain}?date=${item.date}`}
                key={item.date}
              >
                <span>{new Date(`${item.date}T00:00:00`).getDate()} 日</span>
                <small>{item.title}</small>
              </Link>
            ))}
          </div>
        </div>
        <Link className="dailyLatest" href="/industry">
          <strong>全部行业</strong>
          <span>Industry Index</span>
        </Link>
      </aside>

      <main className="dailyDigest">
        <header className="dailyHero">
          <div className="dailyMeta">
            <span />
            <strong>{digest.domain.toUpperCase()}</strong>
            <i>·</i>
            <strong>{digest.storyCount} STORIES</strong>
            <i>·</i>
            <strong>{digest.englishLabel}</strong>
          </div>
          <h1>{digest.label}</h1>
          <div className="dailyDateLine">
            <strong>{formatLongDate(digest.date)}</strong>
            <span />
            <small>{digest.description}</small>
          </div>
        </header>

        {digest.sections.length === 0 ? (
          <section className="emptyState">
            <h2>暂无行业日报内容</h2>
            <p>自动任务生成行业汇报后，这里会显示对应行业的事件摘要。</p>
          </section>
        ) : (
          digest.sections.map((section) => (
            <section className="dailySection" key={section.key}>
              <header className="dailySectionHead">
                <span>{section.index}</span>
                <h2>{section.label}发布/更新</h2>
                <small>{section.englishLabel}</small>
                <b>{section.items.length} 篇</b>
              </header>
              <div className="dailyStoryCard">
                {section.items.map((item) => (
                  <article className="dailyStory" key={item.id}>
                    <Link href={`/events/${item.id}`}>{item.displayTitle}</Link>
                    <div className="dailyStoryMeta">
                      <span>{item.categoryLabel}</span>
                      <small>{item.sourceName}</small>
                    </div>
                    <p>{item.displaySummary || "暂无摘要"}</p>
                  </article>
                ))}
              </div>
            </section>
          ))
        )}
      </main>
    </div>
  );
}

function formatLongDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(date);
}
