import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Globe,
  CalendarClock,
  GitCompare,
  Webhook,
  KeyRound,
  ShieldCheck,
  ScrollText,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCurrentUser, useLogout } from "@/hooks/useAuth";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useSidebar } from "@/hooks/useSidebar";

const NAV_ITEMS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/domains", icon: Globe, label: "Mes domaines" },
  { to: "/scheduled", icon: CalendarClock, label: "Scans planifiés" },
  { to: "/diff", icon: GitCompare, label: "Comparer" },
  { to: "/webhooks", icon: Webhook, label: "Webhooks" },
  { to: "/api-keys", icon: KeyRound, label: "Clés API" },
  { to: "/security", icon: ShieldCheck, label: "Sécurité" },
  { to: "/audit", icon: ScrollText, label: "Journal" },
] as const;

export function Sidebar() {
  const { collapsed, toggle } = useSidebar();
  const location = useLocation();
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  return (
    <aside
      className={cn(
        "flex flex-col h-screen border-r transition-[width] duration-200 shrink-0 overflow-hidden",
        "bg-card dark:bg-card/80 dark:backdrop-blur-xl dark:border-white/[0.07]",
        collapsed ? "w-16" : "w-[220px]"
      )}
    >
      {/* Brand */}
      <div
        className={cn(
          "flex items-center h-14 border-b shrink-0 px-4 gap-2.5",
          collapsed && "justify-center px-0"
        )}
      >
        <div className="w-7 h-7 rounded-lg bg-gradient-brand flex items-center justify-center shrink-0">
          <span className="text-white text-xs font-bold leading-none select-none">W</span>
        </div>
        {!collapsed && (
          <span className="font-semibold text-sm tracking-tight">
            <span className="text-[#6366f1]">Web</span>Guard
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
          const active = location.pathname === to;
          return (
            <Link
              key={to}
              to={to}
              title={collapsed ? label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors",
                active
                  ? "bg-gradient-brand-r text-white font-medium shadow-glow-sm"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground",
                collapsed && "justify-center px-0 w-full"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t p-2 space-y-1 shrink-0">
        <div className={cn("flex", collapsed ? "justify-center" : "px-0.5")}>
          <ThemeToggle />
        </div>

        {/* User row */}
        {collapsed ? (
          <button
            onClick={logout}
            title="Déconnexion"
            className="flex w-full items-center justify-center py-1.5 text-muted-foreground hover:text-foreground transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        ) : (
          <div className="flex items-center gap-2 px-1.5 py-1.5 rounded-lg hover:bg-muted transition-colors group">
            <div className="w-6 h-6 rounded-full bg-gradient-brand flex items-center justify-center shrink-0">
              <span className="text-white text-[10px] font-semibold select-none">
                {(user?.email?.[0] ?? "?").toUpperCase()}
              </span>
            </div>
            <span className="flex-1 text-xs text-muted-foreground truncate min-w-0">
              {user?.email}
            </span>
            <button
              onClick={logout}
              title="Déconnexion"
              className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground transition-all shrink-0"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Collapse toggle */}
        <button
          onClick={toggle}
          title={collapsed ? "Développer" : "Réduire"}
          className={cn(
            "flex w-full items-center py-1.5 text-muted-foreground hover:text-foreground transition-colors text-xs",
            collapsed ? "justify-center" : "gap-2 px-1.5"
          )}
        >
          {collapsed ? (
            <ChevronRight className="h-3.5 w-3.5" />
          ) : (
            <>
              <ChevronLeft className="h-3.5 w-3.5" />
              Réduire
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
