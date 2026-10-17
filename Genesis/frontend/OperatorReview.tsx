import React, { useEffect, useState } from 'react';
import { request } from './api';
import type { CaseRecord, Finding, PrivateAlert, FeedbackEvent, Page, RunDetail } from './types';

export function OperatorReview({ current, token, version, onError, onDirty, navigate, onRun, onComplete }: { current: CaseRecord; token: string; version: number; onError: (error: unknown) => void; onDirty: (dirty: boolean) => void; navigate: (action: () => void) => void; onRun: (id: string) => void; onComplete: (run: RunDetail) => void }) {
  const [selected, setSelected] = useState(current.alerts[0]?.id || '');
  const [detail, setDetail] = useState<PrivateAlert | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<Page<FeedbackEvent>>({ items: [], next_cursor: null });
  const [verdict, setVerdict] = useState('INCONCLUSIVE');
  const [notes, setNotes] = useState('');
  const [override, setOverride] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [fieldError, setFieldError] = useState('');
  const notesRef = React.useRef<HTMLTextAreaElement>(null);
  const complete = detail?.alert.status === 'COMPLETE' && !!detail.alert.current_run_id;
  useEffect(() => { onDirty(!!notes || override !== '' || verdict !== 'INCONCLUSIVE'); }, [notes, override, verdict, onDirty]);
  useEffect(() => { setNotes(''); setOverride(''); setVerdict('INCONCLUSIVE'); setMessage(''); setFieldError(''); }, [selected, token]);
  useEffect(() => {
    const controller = new AbortController();
    setDetail(null);
    if (selected && token) {
      setLoading(true);
      Promise.all([
        request<PrivateAlert>(`/api/operator/alerts/${selected}`, token, { signal: controller.signal }),
        request<Page<FeedbackEvent>>(`/api/operator/alerts/${selected}/feedback`, token, { signal: controller.signal })
      ]).then(async ([alert, events]) => {
        if (controller.signal.aborted) return;
        setDetail(alert); setHistory(events);
        if (refresh > 0 && alert.latest_run?.parent_run_id) {
          const run = await request<RunDetail>(`/api/operator/runs/${alert.latest_run.parent_run_id}`, token, { signal: controller.signal });
          if (!controller.signal.aborted) onComplete(run);
        }
      })
        .catch(error => { if (!controller.signal.aborted) onError(error); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }
    return () => controller.abort();
  }, [selected, token, version, refresh]);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); if (!complete || saving) return;
    if (!notes.trim()) { setFieldError('Add your review notes.'); notesRef.current?.focus(); return; }
    setSaving(true); setFieldError(''); setMessage('');
    try {
      await request(`/api/operator/alerts/${selected}/feedback`, token, { method: 'POST', body: JSON.stringify({ verdict, notes: notes.trim(), override_action: override || null, expected_revision: detail!.alert.feedback_revision }) });
      setNotes(''); setOverride(''); setVerdict('INCONCLUSIVE'); onDirty(false); setMessage('Feedback recorded.'); setRefresh(value => value + 1);
    } catch (error) { setMessage((error as { status?: number }).status === 409 ? 'Feedback changed or triage is incomplete. Refresh status before submitting again.' : 'Feedback was not saved. Your notes are preserved.'); onError(error); }
    finally { setSaving(false); }
  }
  async function moreHistory() {
    if (!history.next_cursor || loading) return;
    setLoading(true);
    try {
      const next = await request<Page<FeedbackEvent>>(`/api/operator/alerts/${selected}/feedback?cursor=${encodeURIComponent(history.next_cursor)}`, token);
      setHistory(previous => ({ ...next, items: [...previous.items, ...next.items] }));
    } catch (error) { onError(error); } finally { setLoading(false); }
  }
  if (!token || !current.alerts.length) return null;
  return <section className="panel operator-review"><div className="panel-heading"><h3>Private alert status</h3><button className="text-button" disabled={loading} onClick={() => setRefresh(refresh + 1)}>Refresh status</button></div>
    <label htmlFor="review-alert">Selected alert</label><select id="review-alert" value={selected} disabled={saving} onChange={event => { const id = event.target.value; navigate(() => setSelected(id)); }}>{current.alerts.map(alert => <option key={alert.id} value={alert.id}>{alert.rule_name}</option>)}</select>
    {loading ? <p role="status">Loading private alert…</p> : detail && <><p>Alert: {detail.alert.status}. Latest run: {detail.latest_run?.state || 'Not run'}.</p>{detail.latest_run?.error_code && <p role="status">{detail.latest_run.error_code}: {detail.latest_run.error_code === 'AI_NOT_CONNECTED' ? 'Live access was unavailable for a step. Inspect the sealed steps for any earlier outcomes.' : 'Check the stored run details before continuing.'}</p>}</>}
    {detail?.latest_run?.parent_run_id && <button className="text-button" onClick={() => onRun(detail.latest_run!.parent_run_id!)}>View run usage</button>}
    {complete && detail && <ValidatedInvestigation detail={detail} />}
    <h3>Analyst review</h3><p id="feedback-gate">{complete ? 'Record your decision for this alert and completed run.' : 'A completed, validated AI investigation is required before feedback.'}</p>
    <form noValidate onSubmit={submit} aria-describedby="feedback-gate"><fieldset disabled={!complete || saving}>
      <div className="form-field"><label htmlFor="review-verdict">Verdict</label><select id="review-verdict" value={verdict} onChange={event => setVerdict(event.target.value)}><option value="INCONCLUSIVE">Inconclusive</option><option value="TRUE_POSITIVE">True positive</option><option value="FALSE_POSITIVE">False positive</option></select></div>
      <div className="form-field"><label htmlFor="review-notes">Review notes</label><textarea className="resize-none" id="review-notes" ref={notesRef} rows={5} maxLength={2000} required value={notes} aria-invalid={!!fieldError} aria-describedby={fieldError ? 'review-notes-error' : undefined} onChange={event => setNotes(event.target.value)} />{fieldError && <span id="review-notes-error" className="field-error">{fieldError}</span>}</div>
      <div className="form-field"><label htmlFor="review-override">Action override (optional)</label><select id="review-override" value={override} onChange={event => setOverride(event.target.value)}><option value="">No override</option>{['ESCALATE', 'REVIEW', 'MONITOR', 'CLOSE'].map(action => <option key={action}>{action}</option>)}</select></div>
      <button className="primary" disabled={!complete || saving} aria-busy={saving}>Save feedback</button>
    </fieldset></form>{message && <p role="status">{message}</p>}
    <h3>Feedback history</h3>{history.items.length ? <ol className="feedback-history">{history.items.map(event => <li key={event.id}><strong>{event.verdict.replaceAll('_', ' ').toLowerCase()}</strong><p>{event.notes}</p><small>Revision {event.revision} · {event.provenance} · {new Date(event.submitted_at).toLocaleString('en-AU', { timeZone: 'UTC' })} UTC</small></li>)}</ol> : <p className="muted">No feedback recorded for this alert.</p>}
    {history.next_cursor && <button className="text-button" disabled={loading} onClick={() => void moreHistory()}>Load more feedback</button>}
  </section>;
}

function Findings({ title, items }: { title: string; items: Finding[] }) {
  return <><h4>{title}</h4>{items.length ? <ul>{items.map((finding, index) => <li key={index}><p>{finding.text}</p><small className="evidence-id">Source IDs: {finding.evidence_ids.join(', ')}</small></li>)}</ul> : <p className="muted">None recorded in this model output.</p>}</>;
}

function ValidatedInvestigation({ detail }: { detail: PrivateAlert }) {
  const { A2, A3, A4 } = detail.outputs;
  return <article className="validated-investigation"><h3>Private investigation brief</h3><p className="muted">Validated model suggestions, not an analyst verdict. Source-ID checks do not establish semantic support; inspect the cited evidence before deciding.</p>
    {detail.alert.priority && <p>Post-triage priority: {detail.alert.priority.replaceAll('_', ' ').toLowerCase()}</p>}
    {A3 && <><dl className="usage-values"><dt>Suggested typology</dt><dd>{A3.primary_typology.replaceAll('_', ' ').toLowerCase()}</dd><dt>Suggested action</dt><dd>{A3.suggested_action.toLowerCase()}</dd><dt>Uncertainty</dt><dd>{A3.uncertainty.toLowerCase()}</dd></dl><Findings title="Classification rationale" items={[A3.rationale]} /></>}
    {A4 && <><Findings title="Overview" items={[A4.overview]} /><Findings title="Key findings" items={A4.key_findings} /><Findings title="Counter-evidence" items={A4.counter_evidence} />{([['Missing information', A4.missing_information], ['Next steps', A4.next_steps], ['Limitations', A4.limitations]] as const).map(([title, values]) => <React.Fragment key={title}><h4>{title}</h4>{values.length ? <ul>{values.map((text, index) => <li key={index}>{text}</li>)}</ul> : <p className="muted">None recorded.</p>}</React.Fragment>)}</>}
    {A2 && <details><summary>Risk explanation</summary><Findings title="Risk findings" items={A2.findings} /><Findings title="Risk counter-evidence" items={A2.counter_evidence} /><h4>Risk limitations</h4>{A2.limitations.length ? <ul>{A2.limitations.map((text, index) => <li key={index}>{text}</li>)}</ul> : <p className="muted">None recorded.</p>}</details>}
  </article>;
}
