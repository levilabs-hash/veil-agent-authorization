/** Types for backend console payloads. The UI never authorizes actions. */

export type Decision = "ALLOW" | "REVIEW" | "BLOCK";

export type DemoRun = {
  scenario: string;
  instruction: string;
  action: string;
  recipient: string | null;
  resource: string | null;
  resource_classification: string | null;
  provenance: string;
  risk: string;
  decision: Decision;
  reason: string;
  matched_policy_rule: string;
  executed: boolean;
  timestamp: string;
};

export type AuditEvent = {
  event_id: string;
  timestamp: string;
  action: string;
  provenance: string;
  resource: string | null;
  risk: string;
  decision: string;
  matched_policy_rule: string;
  executed: boolean;
  reason: string;
};
