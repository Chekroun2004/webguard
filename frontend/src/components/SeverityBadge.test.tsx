import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { SeverityBadge } from "./SeverityBadge";

describe("SeverityBadge", () => {
  it("renders the correct French label for each severity", () => {
    const cases: Array<["info" | "low" | "medium" | "high" | "critical", string]> = [
      ["info", "Info"],
      ["low", "Faible"],
      ["medium", "Moyenne"],
      ["high", "Élevée"],
      ["critical", "Critique"],
    ];

    for (const [severity, label] of cases) {
      const { unmount } = render(<SeverityBadge severity={severity} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it("applies the correct color class for each severity", () => {
    const cases: Array<["info" | "low" | "medium" | "high" | "critical", string]> = [
      ["info", "bg-blue-100"],
      ["low", "bg-green-100"],
      ["medium", "bg-yellow-100"],
      ["high", "bg-orange-100"],
      ["critical", "bg-red-100"],
    ];

    for (const [severity, expectedClass] of cases) {
      const { container, unmount } = render(<SeverityBadge severity={severity} />);
      const badge = container.firstChild as HTMLElement;
      expect(badge.className).toContain(expectedClass);
      unmount();
    }
  });

  it("renders without crashing for an unknown severity", () => {
    render(<SeverityBadge severity={"unknown" as unknown as "info"} />);
    expect(screen.getByText("unknown")).toBeInTheDocument();
  });
});
