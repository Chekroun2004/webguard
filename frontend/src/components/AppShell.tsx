import type { ReactNode } from "react";
import { Sidebar } from "@/components/Sidebar";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="relative flex h-screen overflow-hidden">
      {/* Ambient glow layers — dark mode only */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden dark:block hidden">
        <div className="animate-mesh-1 absolute -top-64 -left-64 h-[600px] w-[600px] rounded-full bg-indigo-600/10 blur-[120px]" />
        <div className="animate-mesh-2 absolute -bottom-48 -right-48 h-[500px] w-[500px] rounded-full bg-violet-600/8 blur-[100px]" />
        <div className="animate-mesh-3 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[400px] w-[400px] rounded-full bg-indigo-500/5 blur-[80px]" />
      </div>

      <Sidebar />
      <div className="relative flex-1 overflow-auto bg-background">{children}</div>
    </div>
  );
}
