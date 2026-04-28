"use client";

import { usePathname } from "next/navigation";

type NavItem = {
  label: string;
  href: string;
};

const primaryItems: NavItem[] = [
  { label: "情报雷达", href: "/" },
  { label: "信源管理", href: "/sources" },
  { label: "运行日志", href: "/runs" },
];

const systemItems: NavItem[] = [{ label: "设置", href: "/settings" }];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="brand">AI HOT</div>
      <nav className="navGroup" aria-label="主导航">
        {primaryItems.map((item) => (
          <a className={isActive(pathname, item.href) ? "navItem active" : "navItem"} href={item.href} key={item.label}>
            <span className="navDot" />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>
      <div className="navSectionLabel">后台</div>
      <nav className="navGroup" aria-label="系统导航">
        {systemItems.map((item) => (
          <a className={isActive(pathname, item.href) ? "navItem active" : "navItem"} href={item.href} key={item.label}>
            <span className="navDot" />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>
    </aside>
  );
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(href);
}
