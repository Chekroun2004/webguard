import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "webguard-theme";

function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  const value = window.localStorage.getItem(STORAGE_KEY);
  if (value === "light" || value === "dark" || value === "system") {
    return value;
  }
  return "system";
}

function systemPrefersDark(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  const effective: "light" | "dark" =
    theme === "system" ? (systemPrefersDark() ? "dark" : "light") : theme;
  if (effective === "dark") {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => readStoredTheme());

  // Apply theme to <html> whenever it changes.
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Follow OS changes while in "system" mode.
  useEffect(() => {
    if (theme !== "system" || typeof window === "undefined" || !window.matchMedia) return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => applyTheme("system");
    media.addEventListener?.("change", handler);
    return () => media.removeEventListener?.("change", handler);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // localStorage may be unavailable (private mode, SSR); ignore.
    }
  }, []);

  const toggle = useCallback(() => {
    setThemeState((prev) => {
      const next: Theme = prev === "light" ? "dark" : prev === "dark" ? "system" : "light";
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  return { theme, setTheme, toggle };
}
