import type { Metadata } from "next";
import "../styles/globals.css";
import { AppShell } from "../components/app-shell";

export const metadata: Metadata = {
  title: "HOT Radar",
  description: "Researcher Intelligence Radar",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
