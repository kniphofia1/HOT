"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Clock3,
  Building2,
  List,
  LogIn,
  Moon,
  Monitor,
  Settings,
  Sun,
  X,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { applyTheme } from "./app-shell";

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

type NavSection = {
  label: string;
  items: NavItem[];
};

const navSections: NavSection[] = [
  {
    label: "AIHOT",
    items: [
      { label: "精选", href: "/", icon: Zap },
      { label: "全部动态", href: "/all", icon: List },
      { label: "报告中心", href: "/industry", icon: Building2 },
      { label: "更新日志", href: "/changelog", icon: Clock3 },
    ],
  },
  {
    label: "管理",
    items: [{ label: "设置", href: "/settings", icon: Settings }],
  },
];

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const pathname = usePathname();

  return (
    <aside className="sidebar" id="app-sidebar">
      <button aria-label="关闭导航" className="sidebarClose" onClick={onClose} type="button">
        <X aria-hidden="true" size={18} />
      </button>
      <Link className="sidebarBrand" href="/" aria-label="返回 AI HOT 首页" onClick={onClose}>
        <BrandLogo />
      </Link>

      <div className="divider" />

      <div className="navSections">
        {navSections.map((section) => (
          <section className="navCluster" key={section.label}>
            <div className="navSectionLabel">{section.label}</div>
            <nav className="sideNav" aria-label={section.label}>
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    className={isActive(pathname, item.href) ? "sideLink sideLinkActive" : "sideLink"}
                    href={item.href}
                    key={item.label}
                    onClick={onClose}
                  >
                    <Icon aria-hidden="true" className="sideIcon" size={18} />
                    <span className="sideLabel">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </section>
        ))}
      </div>

      <div className="sidebarFooter">
        <ThemeToggle />
        <Link className="sideLink sidebarLogin" href="/sources" onClick={onClose}>
          <LogIn aria-hidden="true" className="sideIcon" size={14} />
          <span className="sideLabel">管理后台</span>
        </Link>
      </div>
    </aside>
  );
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(href);
}

function BrandLogo() {
  return (
    <span className="brandLogo" aria-label="AIHOT">
      <span className="brandLogoAi">AI</span>
      <span className="brandLogoOrbit" aria-hidden="true">
        <span className="brandLogoOrbitCore" />
      </span>
      <span className="brandLogoHot">HOT</span>
    </span>
  );
}

function ThemeToggle() {
  return (
    <div className="themeToggle" aria-label="主题">
      <button aria-label="深色" onClick={() => setTheme("dark")} type="button">
        <Moon aria-hidden="true" size={14} />
      </button>
      <button aria-label="跟随系统" onClick={() => setTheme("auto")} type="button">
        <Monitor aria-hidden="true" size={14} />
      </button>
      <button aria-label="浅色" onClick={() => setTheme("light")} type="button">
        <Sun aria-hidden="true" size={14} />
      </button>
    </div>
  );
}

function setTheme(mode: string) {
  window.localStorage.setItem("aihot-theme", mode);
  applyTheme(mode);
}
