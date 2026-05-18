const entries = [
  {
    date: "2026-05-08",
    weekday: "周五",
    items: [
      {
        time: "21:30",
        kind: "更新",
        title: "AIHOT 视觉复刻上线",
        body: "侧边栏、精选流、全部动态、日报、Agent 接入、关于、更新日志和反馈页面切换到 AI HOT editorial 风格。",
      },
      {
        time: "21:10",
        kind: "更新",
        title: "公开时间线 API",
        body: "新增 /api/public/items，将 EventCluster、Evidence 和 RawItem 整理成前端信息流可直接消费的结构。",
      },
      {
        time: "20:50",
        kind: "更新",
        title: "本地反馈箱",
        body: "反馈页提交后写入 feedback_entries，不发送外部消息，不引入登录态。",
      },
    ],
  },
];

export default function ChangelogPage() {
  return (
    <div className="page pageTheme changelogPage">
      <header className="changelogHero">
        <div className="changelogEyebrow">CHANGELOG</div>
        <h1>更新日志</h1>
        <p>最近发生了什么，新功能、调整、下线，都写在这里。</p>
      </header>

      <div className="changelogDays">
        {entries.map((day) => (
          <section className="changelogDay" key={day.date}>
            <header className="changelogDayHead">
              <time dateTime={day.date}>{formatDate(day.date)}</time>
              <span>{day.weekday}</span>
            </header>
            <ol className="changelogEntries">
              {day.items.map((item) => (
                <li className="changelogEntry" key={`${day.date}-${item.time}`}>
                  <aside className="changelogMeta">
                    <time>{item.time}</time>
                    <div>
                      <span aria-hidden="true" />
                      {item.kind}
                    </div>
                  </aside>
                  <div className="changelogContent">
                    <h2>{item.title}</h2>
                    <p>{item.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </div>
  );
}

function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(date);
}
