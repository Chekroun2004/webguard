import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useTheme } from "./useTheme";

describe("useTheme", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("persists the chosen theme to localStorage", () => {
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setTheme("dark");
    });

    expect(localStorage.getItem("webguard-theme")).toBe("dark");
    expect(result.current.theme).toBe("dark");

    act(() => {
      result.current.setTheme("light");
    });

    expect(localStorage.getItem("webguard-theme")).toBe("light");
    expect(result.current.theme).toBe("light");
  });

  it("toggles the `dark` class on documentElement", () => {
    const { result } = renderHook(() => useTheme());

    act(() => {
      result.current.setTheme("dark");
    });
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    act(() => {
      result.current.setTheme("light");
    });
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
