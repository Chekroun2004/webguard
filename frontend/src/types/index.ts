export type Vulnerability = {
  id: number;
  name: string;
  severity: "info" | "low" | "medium" | "high" | "critical";
  description: string;
  recommendation: string;
  evidence: string;
};

export type Scan = {
  id: number;
  url: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  finished_at: string | null;
  findings: Vulnerability[];
};

export type User = {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  role: string;
  created_at: string;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type ScanDiffSummary = {
  id: number;
  url: string;
  created_at: string;
  finished_at: string | null;
  total: number;
};

export type ScanDiff = {
  old_scan: ScanDiffSummary;
  new_scan: ScanDiffSummary;
  added: Vulnerability[];
  removed: Vulnerability[];
  unchanged: Vulnerability[];
};
