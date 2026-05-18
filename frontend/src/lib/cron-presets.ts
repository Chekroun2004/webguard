import cronstrue from "cronstrue/i18n";

export type Preset =
  | { kind: "daily"; hour: number }
  | { kind: "weekly"; hour: number; weekDay: number }
  | { kind: "monthly"; hour: number; monthDay: number };

export function presetToCron(p: Preset): string {
  switch (p.kind) {
    case "daily":
      return `0 ${p.hour} * * *`;
    case "weekly":
      return `0 ${p.hour} * * ${p.weekDay}`;
    case "monthly":
      return `0 ${p.hour} ${p.monthDay} * *`;
  }
}

export function describeCron(expr: string): string {
  try {
    return cronstrue.toString(expr, { locale: "fr" });
  } catch {
    return expr;
  }
}
