const sourceTypes = ["rss", "webpage", "hacker_news", "github_repo", "github_release", "youtube_placeholder"];

export default function SourcesPage() {
  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Sources</p>
        <h1>信源管理</h1>
        <p>管理 RSS、网页监控、Hacker News 与 GitHub watch 的本地信源。</p>
      </header>

      <div className="panelGrid">
        <article className="panel">
          <h2>已支持 Source 类型</h2>
          <div className="tagRow">
            {sourceTypes.map((type) => (
              <span key={type}>{type}</span>
            ))}
          </div>
        </article>
        <article className="panel">
          <h2>范围边界</h2>
          <p>当前不接入国内平台、X、YouTube 真实抓取，也不处理登录态网页。</p>
        </article>
      </div>
    </section>
  );
}
