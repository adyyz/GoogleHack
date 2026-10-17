import React, { useEffect, useRef, useState } from 'react';
import { request } from './api';
import { Dialog } from './Dialog';
import type { Page } from './types';

interface Item {
  id: string; state: string; revision: number; priority: string; hypothesis: string;
  candidate: { id: string; threshold_aud_minor?: number } | null;
  sample_sizes?: { conclusive_reviews: number; target_rule_reviews: number };
  support_feedback_ids: string[]; limitations?: string[]; eligible_to_apply: boolean;
  application_block_reason: string | null; active_policy: { revision: number; policy_version_id: string };
  applied_policy_id?: string; expected_effects: string;
  measured_what_if: { benign_alerts_removed: number; suspicious_alerts_removed: number; baseline: { recall: number | null }; candidate_metrics: { recall: number | null } } | null;
  post_apply: { status: string; reviewed_alerts: number; true_positive: number; false_positive: number; queue_effects?: { excluded_alerts: number } | null };
}
interface Trend { run_id: string; created_at: string; state: string; reviewed_alerts: number; false_positive_reviews: number; reviewed_alert_noise_proportion: number | null }
interface Pattern { id: string; rule_id: string; typology: string; detector_policy_id: string; status: string; revision: number; support_feedback_ids: string[]; snapshot_ids: string[]; support_strength: number }
const words = (value: string) => value.replaceAll('_', ' ').toLowerCase();
type Action = 'approve' | 'reject' | 'apply' | 'rollback';
export function RecommendationQueue({ discardVersion, token, onError, onDirty, navigate }: { discardVersion: number; token: string; onError: (error: unknown) => void; onDirty: (value: boolean) => void; navigate: (action: () => void) => void }) {
  const [items, setItems] = useState<Page<Item>>({ items: [], next_cursor: null });
  const [patterns, setPatterns] = useState<Page<Pattern>>({ items: [], next_cursor: null });
  const [trends, setTrends] = useState<Page<Trend>>({ items: [], next_cursor: null });
  const [selected, setSelected] = useState('');
  const [notes, setNotes] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [message, setMessage] = useState('');
  const [fieldError, setFieldError] = useState('');
  const [confirm, setConfirm] = useState<Action | null>(null);
  const [patternDecision, setPatternDecision] = useState<Pattern | null>(null);
  const [patternNotes, setPatternNotes] = useState('');
  const [patternError, setPatternError] = useState('');
  const patternNotesRef = useRef<HTMLTextAreaElement>(null);
  const notesRef = useRef<HTMLTextAreaElement>(null);
  const row = items.items.find(item => item.id === selected);
  useEffect(() => { setNotes(''); setPatternNotes(''); }, [discardVersion]);
  useEffect(() => { onDirty(!!notes || !!patternNotes); }, [notes, patternNotes, onDirty]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setFailed(false);
    Promise.all([
      request<Page<Item>>('/api/operator/evolution/recommendations', token, { signal: controller.signal }),
      request<Page<Pattern>>('/api/operator/evolution/patterns', token, { signal: controller.signal }),
      request<Page<Trend>>('/api/operator/evolution/trends', token, { signal: controller.signal })
    ]).then(([recommendations, memory, history]) => {
      if (controller.signal.aborted) return;
      setItems(recommendations); setPatterns(memory); setTrends(history);
      setSelected(previous => recommendations.items.some(item => item.id === previous) ? previous : recommendations.items[0]?.id || '');
    }).catch(error => { if (!controller.signal.aborted) { setFailed(true); onError(error); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, refresh]);
  async function more(kind: 'recommendations' | 'patterns' | 'trends') {
    const page = kind === 'recommendations' ? items : kind === 'patterns' ? patterns : trends;
    if (!page.next_cursor || busy) return;
    setBusy(true);
    try {
      if (kind === 'recommendations') {
        const next = await request<Page<Item>>(`/api/operator/evolution/recommendations?cursor=${encodeURIComponent(page.next_cursor)}`, token);
        setItems(previous => ({ ...next, items: [...previous.items, ...next.items] }));
      } else if (kind === 'patterns') {
        const next = await request<Page<Pattern>>(`/api/operator/evolution/patterns?cursor=${encodeURIComponent(page.next_cursor)}`, token);
        setPatterns(previous => ({ ...next, items: [...previous.items, ...next.items] }));
      } else {
        const next = await request<Page<Trend>>(`/api/operator/evolution/trends?cursor=${encodeURIComponent(page.next_cursor)}`, token);
        setTrends(previous => ({ ...next, items: [...previous.items, ...next.items] }));
      }
    } catch (error) { onError(error); } finally { setBusy(false); }
  }
  function prepare(action: Action) {
    if (!notes.trim()) { setFieldError('Explain this recommendation decision.'); notesRef.current?.focus(); return; }
    setFieldError(''); setConfirm(action);
  }
  async function decide(action: Action) {
    if (!row || busy) return;
    setBusy(true); setConfirm(null); setMessage('');
    try {
      const change = action === 'apply' || action === 'rollback';
      await request(`/api/operator/evolution/recommendations/${row.id}/${change ? action : 'review'}`, token, {
        method: change ? 'POST' : 'PUT', body: JSON.stringify(change ? {
          expected_revision: row.revision, expected_policy_revision: row.active_policy.revision, notes: notes.trim()
        } : { expected_revision: row.revision, state: action === 'approve' ? 'APPROVED' : 'REJECTED', notes: notes.trim() })
      });
      setNotes(''); onDirty(false); setRefresh(value => value + 1);
      setMessage(change ? 'Policy updated. Refresh the investigation queue to see current applicability. Existing investigations and verdicts are preserved.' : 'Recommendation decision saved. Approval alone does not change detection.');
    } catch (error) { setMessage('The decision could not be confirmed. Refresh the stored state before trying again; your notes are preserved.'); onError(error); }
    finally { setBusy(false); }
  }
  async function changePattern() {
    if (!patternDecision || busy) return;
    if (!patternNotes.trim()) { setPatternError('Explain the pattern status change.'); patternNotesRef.current?.focus(); return; }
    setBusy(true);
    try {
      await request(`/api/operator/evolution/patterns/${patternDecision.id}`, token, { method: 'PUT', body: JSON.stringify({
        expected_revision: patternDecision.revision, status: patternDecision.status === 'ACTIVE' ? 'RESOLVED' : 'ACTIVE', notes: patternNotes.trim()
      }) });
      setPatternDecision(null); setPatternNotes(''); setPatternError(''); setRefresh(value => value + 1);
    } catch (error) { onError(error); } finally { setBusy(false); }
  }
  return <section className="panel recommendation-queue"><div className="panel-heading"><h3><span aria-hidden="true">🧬 </span>Recommendations and pattern memory</h3><button className="text-button" disabled={busy || loading} onClick={() => setRefresh(value => value + 1)}>Refresh recommendations</button></div>
    <p>AI explanations describe proposed detector changes. Only an explicit operator application changes future detection; historical results stay pinned.</p>
    {loading && <p role="status">Loading stored recommendations…</p>}{failed && <p role="status">Recommendations could not be loaded. Refresh to try again.</p>}
    {!loading && !failed && <>
      <div className="form-field"><label htmlFor="recommendation-choice">Recommendation</label><select id="recommendation-choice" value={selected} disabled={busy || !items.items.length} onChange={event => { const value = event.target.value; navigate(() => { setNotes(''); setSelected(value); }); }}><option value="">No recommendation selected</option>{items.items.map(item => <option key={item.id} value={item.id}>{item.priority} / {item.candidate?.id || 'Evidence finding'} / {words(item.state)}</option>)}</select></div>
      {!items.items.length && <p>No recommendation items yet. Complete an A5 analysis to store its findings.</p>}
      {row && <article><h4>{row.priority} / {row.candidate?.id || 'Evidence finding'} / {words(row.state)}</h4><p>{row.hypothesis}</p><dl className="usage-values"><dt>Current policy</dt><dd className="evidence-id">{row.active_policy.policy_version_id}</dd><dt>Proposed change</dt><dd>{row.candidate ? row.candidate.id + (row.candidate.threshold_aud_minor ? ` / AUD ${row.candidate.threshold_aud_minor / 100}` : '') : 'No supported detector change'}</dd><dt>Review sample</dt><dd>{row.sample_sizes ? `${row.sample_sizes.conclusive_reviews} overall / ${row.sample_sizes.target_rule_reviews} target rule` : 'See original analysis'}</dd><dt>Supporting reviews</dt><dd>{row.support_feedback_ids.length}</dd></dl>
        <h4>Before application: measured what-if</h4>{row.measured_what_if ? <p>{row.measured_what_if.benign_alerts_removed} benign alerts removed / {row.measured_what_if.suspicious_alerts_removed} suspicious alerts removed. Recall {row.measured_what_if.baseline.recall ?? 'Unavailable'} → {row.measured_what_if.candidate_metrics.recall ?? 'Unavailable'}. Synthetic reference replay only.</p> : <p>No stored comparison for this recommendation.</p>}
        <p>{row.expected_effects}</p>{row.application_block_reason && <p className="context-warning">{row.application_block_reason}</p>}{row.limitations?.length ? <ul>{row.limitations.map((text, index) => <li key={index}>{text}</li>)}</ul> : null}
        <h4>After application: observed effects</h4><p>{row.post_apply.status === 'NOT_YET_OBSERVED' ? 'Not yet observed' : `${row.post_apply.reviewed_alerts} reviewed alerts / ${row.post_apply.true_positive} true positive / ${row.post_apply.false_positive} false positive. Reviewed outcomes only; no causal improvement claim.`}</p>{row.post_apply.queue_effects && <p>{row.post_apply.queue_effects.excluded_alerts} demo alerts excluded by the applied policy. Frozen and in-progress work remains auditable.</p>}
        <form noValidate onSubmit={event => { event.preventDefault(); prepare('approve'); }}><fieldset disabled={busy}><div className="form-field"><label htmlFor="recommendation-notes">Recommendation decision notes</label><textarea id="recommendation-notes" ref={notesRef} className="resize-none" rows={4} maxLength={2000} value={notes} aria-invalid={!!fieldError} aria-describedby={fieldError ? 'recommendation-error' : undefined} onChange={event => setNotes(event.target.value)} />{fieldError && <span id="recommendation-error" className="field-error">{fieldError}</span>}</div><div className="dialog-actions"><button className="primary" disabled={!row.eligible_to_apply || !['PROPOSED', 'REVIEWED'].includes(row.state)}>Approve recommendation</button><button className="text-button" type="button" disabled={!['PROPOSED', 'APPROVED', 'REVIEWED'].includes(row.state)} onClick={() => prepare('reject')}>Reject recommendation</button><button className="primary" type="button" disabled={!row.eligible_to_apply || row.state !== 'APPROVED'} onClick={() => prepare('apply')}>Apply approved policy</button><button className="text-button" type="button" disabled={row.state !== 'APPLIED' || row.active_policy.policy_version_id !== row.applied_policy_id} onClick={() => prepare('rollback')}>Roll back policy</button></div></fieldset></form>
      </article>}
      {items.next_cursor && <button className="text-button" disabled={busy} onClick={() => void more('recommendations')}>Load more recommendations</button>}
      <h4>Recurring false-positive patterns</h4><p className="muted">Distinct analyst reviews build heuristic support strength, not statistical confidence. Repeated snapshots do not add support.</p>
      {patterns.items.length ? <div className="table-scroll"><table><thead><tr><th>Detector</th><th>Typology</th><th>Distinct FP reviews</th><th>Support strength</th><th>Status</th></tr></thead><tbody>{patterns.items.map(pattern => <tr key={pattern.id}><td>{words(pattern.rule_id)}</td><td>{words(pattern.typology)}</td><td>{pattern.support_feedback_ids.length}</td><td>{pattern.support_strength.toFixed(2)}</td><td>{words(pattern.status)} <button className="text-button" disabled={busy} onClick={() => { setPatternDecision(pattern); setPatternError(''); }}>{pattern.status === 'ACTIVE' ? 'Resolve pattern' : 'Reopen pattern'}</button></td></tr>)}</tbody></table></div> : <p>No recurring false-positive pattern recorded. True-positive and inconclusive reviews do not create FP patterns.</p>}
      {patterns.next_cursor && <button className="text-button" disabled={busy} onClick={() => void more('patterns')}>Load more patterns</button>}
      <h4>Review trend across analyses</h4><p className="muted">Cumulative reviewed-alert noise by frozen input snapshot. Samples overlap across runs; this is not population FPR or proof that a policy caused improvement.</p>
      {trends.items.length ? <div className="table-scroll"><table><thead><tr><th>Analysis / UTC</th><th>State</th><th>Reviewed alerts</th><th>False positives</th><th>Reviewed-alert noise</th></tr></thead><tbody>{trends.items.map(trend => <tr key={trend.run_id}><td>{new Date(trend.created_at).toLocaleString('en-AU', { timeZone: 'UTC' })}</td><td>{words(trend.state)}</td><td>{trend.reviewed_alerts}</td><td>{trend.false_positive_reviews}</td><td>{trend.reviewed_alert_noise_proportion === null ? 'Unavailable' : new Intl.NumberFormat('en-AU', { style: 'percent', maximumFractionDigits: 1 }).format(trend.reviewed_alert_noise_proportion)}</td></tr>)}</tbody></table></div> : <p>No analysis history yet.</p>}
      {trends.next_cursor && <button className="text-button" disabled={busy} onClick={() => void more('trends')}>Load more review trends</button>}
    </>}{message && <p role="status">{message}</p>}
    {patternDecision && <Dialog title="Change pattern status?" description="Record why this recurring pattern is resolved or active. This does not change detection policies." onClose={() => { setPatternDecision(null); setPatternNotes(''); setPatternError(''); }}><div className="form-field"><label htmlFor="pattern-notes">Pattern status notes</label><textarea id="pattern-notes" ref={patternNotesRef} className="resize-none" rows={4} maxLength={2000} value={patternNotes} aria-invalid={!!patternError} aria-describedby={patternError ? 'pattern-error' : undefined} onChange={event => setPatternNotes(event.target.value)} />{patternError && <span id="pattern-error" className="field-error">{patternError}</span>}</div><div className="dialog-actions"><button className="text-button" onClick={() => { setPatternDecision(null); setPatternNotes(''); }}>Keep reviewing</button><button className="primary" disabled={busy} onClick={() => void changePattern()}>Save pattern status</button></div></Dialog>}
    {confirm && <Dialog title={confirm === 'apply' ? 'Apply detector policy?' : confirm === 'rollback' ? 'Roll back detector policy?' : 'Save recommendation decision?'} description={confirm === 'apply' ? 'Apply this supported detector policy to future queue generations and runs. Existing investigations and saved verdicts retain their original versions.' : confirm === 'rollback' ? 'Restore the previous policy for future runs. Historical outcomes and the application audit remain unchanged.' : 'Record your explicit decision and notes. Approval does not apply the policy.'} onClose={() => setConfirm(null)}><div className="dialog-actions"><button className="text-button" onClick={() => setConfirm(null)}>Keep reviewing</button><button className="primary" disabled={busy} onClick={() => void decide(confirm)}>Confirm decision</button></div></Dialog>}
  </section>;
}
