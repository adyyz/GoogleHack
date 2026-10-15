export interface Transaction { id: string; occurred_at: string; amount_aud_minor: number; original_minor: number; currency: string; type: string; direction: string; counterparty_id: string | null; description: string }
export interface CaseRecord {
  id: string; name: string; scenario_family: string; ai_status: string;
  alerts: { id: string; rule_name: string; rule_id: string; status: string }[];
  evidence: { trigger: Transaction; history: Transaction[]; customer: { display_name: string; profile_context: string }; signals: string[]; protected_signals: string[]; missing_context: string[]; facts: { window_count: number; window_volume_aud_minor: number; cash_ratio: number | null; currency_count: number }; evidence_ids: string[] };
  risk: { overall_score: number | null; tier: string; dimensions: Record<string, number | null>; weights: Record<string, number> };
}
export interface Evaluation { purpose: string; warning: string; discovery_preview: { candidate: { id: string }; baseline: { TP: number; FP: number; TN: number; FN: number; recall: number | null }; candidate_metrics: { TP: number; FP: number; TN: number; FN: number; recall: number | null }; benign_alerts_removed: number; suspicious_alerts_removed: number; result: string }[] }
