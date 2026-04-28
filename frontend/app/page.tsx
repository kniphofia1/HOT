const milestones = [
  {
    time: "Milestone 1",
    title: "工程底座与数据层",
    description: "当前只实现 Docker Compose、前后端壳、迁移、核心表结构和 Source CRUD。",
    score: 1,
    reason: "当前允许执行范围",
  },
  {
    time: "Blocked",
    title: "真实抓取与事件流",
    description: "RSS、HN、GitHub、网页抓取、AI 聚类、评分和简报导出全部留到后续 Milestone。",
    score: 0,
    reason: "避免提前越界",
  },
];

export default function RadarPage() {
  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Researcher Intelligence Radar</p>
        <h1>情报雷达</h1>
        <p>Milestone 1 页面壳。当前不展示真实事件流，也不触发任何抓取。</p>
      </header>

      <div className="timeline">
        {milestones.map((item) => (
          <article className="eventCard" key={item.title}>
            <div className="eventTime">{item.time}</div>
            <div className="eventBody">
              <div className="eventMeta">本地单机闭环 / v0.1</div>
              <div className="eventTitleRow">
                <h2>{item.title}</h2>
                <span className="scoreBadge">{item.score}</span>
              </div>
              <p>{item.description}</p>
              <div className="tagRow">
                <span>Source</span>
                <span>RawItem</span>
                <span>Connector</span>
              </div>
              <div className="reasonBar">推荐理由：{item.reason}</div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
