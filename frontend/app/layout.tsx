import type { Metadata } from "next";
import "../styles/globals.css";
import { AppShell } from "../components/app-shell";

export const metadata: Metadata = {
  title: "AIHOT",
  description: "Self-hosted AI monitoring for research intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#060814" media="(prefers-color-scheme: dark)" />
        <meta name="theme-color" content="#fafbfc" media="(prefers-color-scheme: light)" />
        <meta id="theme-color-dynamic" name="theme-color" content="#060814" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
(function(){
  try {
    var saved = localStorage.getItem('aihot-theme');
    var mode = (saved === 'dark' || saved === 'light' || saved === 'auto') ? saved : 'dark';
    var actual = mode === 'auto' ? (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark') : mode;
    document.documentElement.setAttribute('data-theme', actual);
    document.documentElement.setAttribute('data-theme-mode', mode);
    var meta = document.getElementById('theme-color-dynamic');
    if (meta) meta.setAttribute('content', actual === 'light' ? '#fafbfc' : '#060814');
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.documentElement.setAttribute('data-theme-mode', 'dark');
  }
})();
`,
          }}
        />
      </head>
      <body suppressHydrationWarning>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
