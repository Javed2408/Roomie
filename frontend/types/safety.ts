/** Why something is being reported. Mirrors `reports.reason` in the schema. */
export type ReportReason =
  | "FAKE_OR_MISLEADING"
  | "HARASSMENT"
  | "SCAM_OR_FRAUD"
  | "UNAUTHORISED_BROKER"
  | "INAPPROPRIATE_CONTENT"
  | "OTHER";

export const REPORT_REASON_LABELS: Record<ReportReason, string> = {
  FAKE_OR_MISLEADING: "Fake or misleading information",
  HARASSMENT: "Harassment or abusive behaviour",
  SCAM_OR_FRAUD: "Scam or request for money",
  UNAUTHORISED_BROKER: "Unauthorised broker or undisclosed fees",
  INAPPROPRIATE_CONTENT: "Inappropriate content",
  OTHER: "Something else",
};

/** What can be reported. Blocking only applies to people. */
export type SafetyTargetKind = "person" | "listing";
