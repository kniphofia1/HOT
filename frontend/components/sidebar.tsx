type NavItem = {
  label: string;
  href: string;
  active?: boolean;
};

const primaryItems: NavItem[] = [
  { label: "情报雷达", href: "/", active: true },
  { label: "信源管理", href: "/sources" },
  { label: "网页监控", href: "#" },
  { label: "GitHub Watch", href: "#" },
  { label: "运行日志", href: "#" },
  { label: "简报", href: "#" },
];

const systemItems: NavItem[] = [{ label: "设置", href: "/settings" }];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">AI HOT</div>
      <nav className="navGroup" aria-label="主导航">
        {primaryItems.map((item) => (
          <a className={item.active ? "navItem active" : "navItem"} href={item.href} key={item.label}>
            <span className="navDot" />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>
      <div className="navSectionLabel">后台</div>
      <nav className="navGroup" aria-label="系统导航">
        {systemItems.map((item) => (
          <a className="navItem" href={item.href} key={item.label}>
            <span className="navDot" />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>
    </aside>
  );
}
