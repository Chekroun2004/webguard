import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
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
import { LanguageToggle } from "@/components/LanguageToggle";
import { useSidebar } from "@/hooks/useSidebar";

const NAV_KEYS = [
  { to: "/dashboard", icon: LayoutDashboard, key: "nav.dashboard" },
  { to: "/domains", icon: Globe, key: "nav.domains" },
  { to: "/scheduled", icon: CalendarClock, key: "nav.scheduled" },
  { to: "/diff", icon: GitCompare, key: "nav.diff" },
  { to: "/webhooks", icon: Webhook, key: "nav.webhooks" },
  { to: "/api-keys", icon: KeyRound, key: "nav.api_keys" },
  { to: "/security", icon: ShieldCheck, key: "nav.security" },
  { to: "/audit", icon: ScrollText, key: "nav.audit" },
] as const;

export function Sidebar() {
  const { collapsed, toggle } = useSidebar();
  const location = useLocation();
  const { data: user } = useCurrentUser();
  const logout = useLogout();
  const { t } = useTranslation();

  return (
    <aside
      className={cn(
        "flex flex-col h-screen border-r transition-[width] duration-200 shrink-0 overflow-hidden",
        "bg-card dark:bg-card/80 dark:backdrop-blur-xl dark:border-white/[0.07]",
        collapsed ? "w-16" : "w-[220px]"
      )}
    >
      {/* Brand */}
      <Link
        to="/dashboard"
        className={cn(
          "flex items-center h-14 border-b shrink-0 px-4 gap-2.5 hover:opacity-80 transition-opacity",
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
      </Link>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV_KEYS.map(({ to, icon: Icon, key }) => {
          const active = location.pathname === to;
          const label = t(key);
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
        <div className={cn("flex gap-1", collapsed ? "justify-center flex-col items-center" : "px-0.5")}>
          <ThemeToggle />
          {!collapsed && <LanguageToggle />}
        </div>

        {/* User row */}
        {collapsed ? (
          <button
            onClick={logout}
            title={t("nav.logout")}
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
          title={collapsed ? t("nav.expand") : t("nav.collapse")}
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
              {t("nav.collapse")}
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
