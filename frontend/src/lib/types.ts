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
  review_id?: string | null;
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
  related_event_id?: string | null;
  review_status?: string | null;
  approval_source?: string | null;
};

export type ReviewResolution = {
  decision: {
    decision: Decision;
    reason: string;
    matched_policy_rule: string;
    provenance: string;
    requested_action: string;
    target_resource: string | null;
    risk_classification: string;
  };
  executed: boolean;
  review_id: string | null;
  related_event_id: string | null;
};
