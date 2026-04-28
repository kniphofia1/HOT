const sourceTypes = ["rss", "webpage", "hacker_news", "github_repo", "github_release", "youtube_placeholder"];

export default function SourcesPage() {
  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Milestone 1</p>
        <h1>信源管理</h1>
        <p>本阶段只提供页面壳和 Source CRUD 的接口目标，不实现真实抓取。</p>
      </header>

      <div className="panelGrid">
        <article className="panel">
          <h2>允许的 Source 类型</h2>
          <div className="tagRow">
            {sourceTypes.map((type) => (
              <span key={type}>{type}</span>
            ))}
          </div>
        </article>
        <article className="panel">
          <h2>当前禁止</h2>
          <p>RSS/HN/GitHub/网页真实抓取、AI 聚类、Markdown 简报导出、YouTube 真实 API 请求。</p>
        </article>
      </div>
    </section>
  );
}
