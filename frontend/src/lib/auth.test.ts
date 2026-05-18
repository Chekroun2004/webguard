import { beforeEach, describe, expect, it } from "vitest";

import { tokenStorage } from "./auth";

describe("tokenStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("setTokens persists both tokens to localStorage", () => {
    tokenStorage.setTokens("access-abc", "refresh-xyz");

    expect(localStorage.getItem("wg_access")).toBe("access-abc");
    expect(localStorage.getItem("wg_refresh")).toBe("refresh-xyz");
    expect(tokenStorage.getAccess()).toBe("access-abc");
    expect(tokenStorage.getRefresh()).toBe("refresh-xyz");
  });

  it("clear removes both tokens from localStorage", () => {
    tokenStorage.setTokens("a", "b");
    expect(tokenStorage.getAccess()).toBe("a");

    tokenStorage.clear();

    expect(localStorage.getItem("wg_access")).toBeNull();
    expect(localStorage.getItem("wg_refresh")).toBeNull();
    expect(tokenStorage.getAccess()).toBeNull();
    expect(tokenStorage.getRefresh()).toBeNull();
  });
});
