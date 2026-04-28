import { Sidebar } from "./sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="appShell">
      <Sidebar />
      <main className="mainPanel">{children}</main>
    </div>
  );
}
