export default function SettingsPage() {
  return (
    <section className="pageStack">
      <header className="pageHeader">
        <p className="eyebrow">Local Settings</p>
        <h1>设置</h1>
        <p>Milestone 1 只保留配置入口壳，不读取或展示真实密钥。</p>
      </header>

      <div className="panelGrid">
        <article className="panel">
          <h2>环境变量</h2>
          <p>真实配置应写入本地 .env，并保持不提交。模板见仓库根目录 .env.example。</p>
        </article>
        <article className="panel">
          <h2>后续配置</h2>
          <p>AI provider、GitHub token、默认刷新频率和数据保留天数将在后续 Milestone 完整接入。</p>
        </article>
      </div>
    </section>
  );
}
