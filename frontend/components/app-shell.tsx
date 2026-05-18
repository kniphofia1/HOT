"use client";

import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Sidebar } from "./sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem("aihot-theme");
    const mode = saved === "light" || saved === "auto" || saved === "dark" ? saved : "dark";
    applyTheme(mode);
  }, []);

  return (
    <div className="appShell" data-sidebar-open={sidebarOpen ? "true" : "false"}>
      <button
        aria-controls="app-sidebar"
        aria-expanded={sidebarOpen}
        aria-label="打开导航"
        className="appHamburger"
        onClick={() => setSidebarOpen(true)}
        type="button"
      >
        <Menu aria-hidden="true" size={18} />
      </button>
      <div className={sidebarOpen ? "sidebarBackdrop isOpen" : "sidebarBackdrop"} onClick={() => setSidebarOpen(false)} />
      <Sidebar onClose={() => setSidebarOpen(false)} />
      <main className="appMain">{children}</main>
    </div>
  );
}

export function applyTheme(mode: string) {
  const root = document.documentElement;
  const actual =
    mode === "auto" && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : mode === "light" ? "light" : "dark";
  root.setAttribute("data-theme", actual);
  root.setAttribute("data-theme-mode", mode);
  if (document.body) {
    document.body.setAttribute("arco-theme", actual);
  }
  const meta = document.getElementById("theme-color-dynamic");
  if (meta) {
    meta.setAttribute("content", actual === "light" ? "#fafbfc" : "#060814");
  }
}
