import { Monitor, Moon, Sun } from "lucide-react";

import { useTheme } from "@/hooks/useTheme";

const LABELS = {
  light: "Thème clair (cliquer pour passer en sombre)",
  dark: "Thème sombre (cliquer pour suivre le système)",
  system: "Thème système (cliquer pour passer en clair)",
} as const;

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const label = LABELS[theme];

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-transparent text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
    >
      {theme === "light" && <Sun className="h-4 w-4" aria-hidden="true" />}
      {theme === "dark" && <Moon className="h-4 w-4" aria-hidden="true" />}
      {theme === "system" && <Monitor className="h-4 w-4" aria-hidden="true" />}
    </button>
  );
}
