import type { ReactNode } from "react";
import { Sidebar } from "@/components/Sidebar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 overflow-auto bg-background">{children}</div>
    </div>
  );
}
