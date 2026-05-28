export type AuditAction =
  | "scan.create"
  | "scheduled.create"
  | "scheduled.update"
  | "scheduled.delete"
  | "domain.create"
  | "api_key.create"
  | "api_key.revoke"
  | "webhook.create"
  | "webhook.delete"
  | "webhook.test"
  | "totp.enable"
  | "totp.disable";

export type AuditStatus = "success" | "failure";

export interface AuditEvent {
  id: number;
  user_id: number;
  action: AuditAction;
  target_type: string | null;
  target_id: number | null;
  status: AuditStatus;
  ip: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditEventList {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditFilters {
  page: number;
  pageSize: number;
  action?: AuditAction;
  status?: AuditStatus;
  dateFrom?: string; // YYYY-MM-DD
  dateTo?: string; // YYYY-MM-DD
}

export const ACTION_LABELS: Record<AuditAction, string> = {
  "scan.create": "Création scan",
  "scheduled.create": "Création scan planifié",
  "scheduled.update": "Mise à jour scan planifié",
  "scheduled.delete": "Suppression scan planifié",
  "domain.create": "Ajout domaine",
  "api_key.create": "Création clé API",
  "api_key.revoke": "Révocation clé API",
  "webhook.create": "Création webhook",
  "webhook.delete": "Suppression webhook",
  "webhook.test": "Test webhook",
  "totp.enable": "Activation 2FA",
  "totp.disable": "Désactivation 2FA",
};
