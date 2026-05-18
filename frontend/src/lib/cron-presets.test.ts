import { describe, expect, it } from "vitest";
import { describeCron, presetToCron } from "./cron-presets";

describe("presetToCron", () => {
  it("daily at hour", () => {
    expect(presetToCron({ kind: "daily", hour: 9 })).toBe("0 9 * * *");
  });

  it("weekly on Monday at 09:00", () => {
    expect(presetToCron({ kind: "weekly", hour: 9, weekDay: 1 })).toBe(
      "0 9 * * 1",
    );
  });

  it("monthly on day 1 at 09:00", () => {
    expect(presetToCron({ kind: "monthly", hour: 9, monthDay: 1 })).toBe(
      "0 9 1 * *",
    );
  });
});

describe("describeCron", () => {
  it("describes a daily expression in French", () => {
    expect(describeCron("0 9 * * *")).toMatch(/9/);
  });

  it("returns the raw expression if invalid", () => {
    expect(describeCron("garbage")).toBe("garbage");
  });
});
