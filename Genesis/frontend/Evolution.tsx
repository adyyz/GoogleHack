import React, { useEffect, useRef, useState } from 'react';
import { request } from './api';
import { Dialog } from './Dialog';
import { UsageDisplay } from './Usage';
import { RuleIntelligence } from './RuleIntelligence';
import { A0Learning } from './A0Learning';
import { RecommendationQueue } from './RecommendationQueue';
import type { AnalyticalSnapshot, EvolutionDetail, EvolutionRun, FreezeOption, FrozenEvaluation, Page, RunDetail } from './types';

const words = (value: string) => value.toLowerCase().replaceAll('_', ' ');
const utc = (value: string) => new Date(value).toLocaleString('en-AU', { timeZone: 'UTC' }) + ' UTC';
type Props = { selectedRule: string; onSelectRule: (value: string) => void; onOpenCase: (caseId: string, alertId: string, rule: string) => void; token: string; canRun: boolean; onError: (error: unknown) => void; onDirty: (dirty: boolean) => void; navigate: (action: () => void) => void; onRun: (id: string) => void };

export function Evolution({ token, canRun, onError, onDirty, navigate: guardNavigation, onRun, selectedRule, onSelectRule, onOpenCase }: Props) {
  const [discardVersion, setDiscardVersion] = useState(0);
  function navigate(action: () => void) {
    guardNavigation(() => { setFreezeNotes(''); setReviewNotes(''); setReviewState('APPROVED'); setDiscardVersion(value => value + 1); action(); });
  }
  const [snapshots, setSnapshots] = useState<Page<AnalyticalSnapshot>>({ items: [], next_cursor: null });
  const [runs, setRuns] = useState<Page<EvolutionRun>>({ items: [], next_cursor: null });
  const [selectedSnapshot, setSelectedSnapshot] = useState('');
  const [selectedRun, setSelectedRun] = useState('');
  const [detail, setDetail] = useState<EvolutionDetail | null>(null);
  const [frozen, setFrozen] = useState<FrozenEvaluation>({ freeze: null, simulation: null });
  const [options, setOptions] = useState<FreezeOption[]>([]);
  const [candidate, setCandidate] = useState('');
  const [freezeNotes, setFreezeNotes] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [recommendationDirty, setRecommendationDirty] = useState(false);
  const [intelligenceDirty, setIntelligenceDirty] = useState(false);
  const [learningDirty, setLearningDirty] = useState(false);
  const [reviewState, setReviewState] = useState('APPROVED');
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [fieldError, setFieldError] = useState<'freeze' | 'review' | null>(null);
  const [confirm, setConfirm] = useState<'a5' | 'freeze' | 'simulate' | null>(null);
  const freezeRef = useRef<HTMLTextAreaElement>(null);
  const reviewRef = useRef<HTMLTextAreaElement>(null);
  const lifetime = useRef(new AbortController());
  useEffect(() => () => lifetime.current.abort(), []);
  useEffect(() => { onDirty(!!freezeNotes || !!reviewNotes || reviewState !== 'APPROVED' || recommendationDirty || intelligenceDirty || learningDirty); }, [freezeNotes, reviewNotes, reviewState, recommendationDirty, intelligenceDirty, learningDirty, onDirty]);
  const snapshot = snapshots.items.find(item => item.id === selectedSnapshot);
  const option = options.find(item => item.candidate.id === candidate);
  function clearDrafts() { setFreezeNotes(''); setReviewNotes(''); setReviewState('APPROVED'); setFieldError(null); }
  function fail(cause: unknown) {
    setError((cause as { status?: number }).status === 409 ? 'The stored state changed or an evidence gate is closed. Refresh Evolution data before continuing. Your notes are preserved.' : 'The request could not be confirmed. Refresh Evolution data to check its stored state before trying again. Your notes are preserved.');
    onError(cause);
  }
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    Promise.all([
      request<Page<AnalyticalSnapshot>>('/api/operator/evolution/snapshots', token, { signal: controller.signal }),
      request<Page<EvolutionRun>>('/api/operator/evolution/runs', token, { signal: controller.signal }),
      request<FrozenEvaluation>('/api/operator/evolution/freeze', token, { signal: controller.signal }),
      request<{ options: FreezeOption[] }>('/api/operator/evolution/candidates', token, { signal: controller.signal })
    ]).then(([inputs, history, stored, allowlist]) => {
      if (controller.signal.aborted) return;
      setSnapshots(previous => ({ ...inputs, items: [...inputs.items, ...previous.items.filter(item => item.id === selectedSnapshot && !inputs.items.some(row => row.id === item.id))] }));
      setRuns(previous => ({ ...history, items: [...history.items, ...previous.items.filter(item => item.id === selectedRun && !history.items.some(row => row.id === item.id))] }));
      setFrozen(stored); setOptions(allowlist.options);
      setSelectedSnapshot(previous => previous || inputs.items[0]?.id || '');
      setSelectedRun(previous => previous || history.items[0]?.id || '');
    }).catch(cause => { if (!controller.signal.aborted) fail(cause); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, refresh]);
  useEffect(() => {
    const controller = new AbortController(); setDetail(null);
    if (selectedRun) {
      setDetailLoading(true);
      request<EvolutionDetail>(`/api/operator/evolution/runs/${selectedRun}`, token, { signal: controller.signal })
        .then(result => { if (!controller.signal.aborted) setDetail(result); })
        .catch(cause => { if (!controller.signal.aborted) fail(cause); })
        .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    } else setDetailLoading(false);
    return () => controller.abort();
  }, [selectedRun, token, refresh]);
  async function mutate(action: 'snapshot' | 'a5' | 'freeze' | 'simulate' | 'review') {
    if (busy) return;
    setConfirm(null); setBusy(true); setError(''); setMessage('');
    const signal = lifetime.current.signal;
    try {
      if (action === 'snapshot') {
        const result = await request<AnalyticalSnapshot>('/api/operator/evolution/snapshots', token, { method: 'POST', signal });
        if (signal.aborted) return;
        setSelectedSnapshot(result.id); setMessage('Analytical snapshot stored. Repeated inputs return the same record.');
      } else if (action === 'a5' && snapshot) {
        const result = await request<RunDetail>('/api/operator/evolution/runs', token, { method: 'POST', signal, body: JSON.stringify({ snapshot_id: snapshot.id }) });
        if (signal.aborted) return;
        setSelectedRun(result.id); setMessage(`Evolution analysis ${words(result.state)}${result.error_code ? ': ' + result.error_code : ''}. Refresh after the separate worker finishes.`);
      } else if (action === 'freeze' && detail?.result && option) {
        await request('/api/operator/evolution/freezes', token, { method: 'POST', signal, body: JSON.stringify({ evolution_run_id: selectedRun, candidate_id: candidate, expected_candidate_hash: option.candidate_hash, notes: freezeNotes.trim() }) });
        if (signal.aborted) return;
        setFreezeNotes(''); setMessage('Detector candidate frozen. Held-out data has not been evaluated by this action.');
      } else if (action === 'simulate' && frozen.freeze) {
        const result = await request<NonNullable<FrozenEvaluation['simulation']>>(`/api/operator/evolution/freezes/${frozen.freeze.id}/simulation`, token, { method: 'POST', signal });
        if (signal.aborted) return;
        setMessage(`Held-out comparison ${words(result.state)}. Repeated requests return this stored record.`);
      } else if (action === 'review' && detail?.recommendation) {
        await request(`/api/operator/evolution/recommendations/${detail.recommendation.id}/review`, token, { method: 'PUT', signal, body: JSON.stringify({ expected_revision: detail.recommendation.revision, state: reviewState, notes: reviewNotes.trim() }) });
        if (signal.aborted) return;
        setReviewNotes(''); setReviewState('APPROVED'); setMessage('Recommendation review saved. No monitoring change was applied.');
      }
      if (!signal.aborted) setRefresh(value => value + 1);
    } catch (cause) { if (!signal.aborted) fail(cause); }
    finally { if (!signal.aborted) setBusy(false); }
  }
  async function more(kind: 'snapshots' | 'runs') {
    const page = kind === 'snapshots' ? snapshots : runs;
    if (!page.next_cursor || busy) return;
    setBusy(true); const signal = lifetime.current.signal;
    try {
      const next = await request<Page<AnalyticalSnapshot> & Page<EvolutionRun>>(`/api/operator/evolution/${kind}?cursor=${encodeURIComponent(page.next_cursor)}`, token, { signal });
      if (signal.aborted) return;
      if (kind === 'snapshots') setSnapshots(previous => ({ ...next, items: [...previous.items, ...next.items] }));
      else setRuns(previous => ({ ...next, items: [...previous.items, ...next.items] }));
    } catch (cause) { if (!signal.aborted) fail(cause); } finally { if (!signal.aborted) setBusy(false); }
  }
  function prepareFreeze(event: React.FormEvent) {
    event.preventDefault(); if (busy || !detail?.result || !option) return;
    if (!freezeNotes.trim()) { setFieldError('freeze'); freezeRef.current?.focus(); return; }
    setFieldError(null); setConfirm('freeze');
  }
  function review(event: React.FormEvent) {
    event.preventDefault(); if (busy) return;
    if (!reviewNotes.trim()) { setFieldError('review'); reviewRef.current?.focus(); return; }
    setFieldError(null); void mutate('review');
  }
  return <div className="evolution-evidence" aria-busy={loading || busy}>
    <RuleIntelligence discardVersion={discardVersion} version={refresh} token={token} detail={detail} selectedRule={selectedRule} onSelectRule={onSelectRule} onOpenCase={onOpenCase} onDirty={setIntelligenceDirty} navigate={navigate} onError={onError} /><A0Learning discardVersion={discardVersion} token={token} snapshotId={selectedSnapshot} selectedRule={selectedRule} onDirty={setLearningDirty} navigate={navigate} onError={onError} onChanged={() => setRefresh(value => value + 1)} />
    <section className="panel"><div className="panel-heading"><h3>Stored Evolution evidence</h3><button className="text-button" disabled={loading || busy} onClick={() => setRefresh(value => value + 1)}>Refresh Evolution data</button></div>
      <p>Human verdicts, model suggestions and deterministic comparison results remain separate. Refresh explicitly after a worker run.</p>
      {loading && <p role="status">Loading Evolution evidence…</p>}{error && <p className="error" role="alert">{error}</p>}{message && <p role="status">{message}</p>}
      <button className="primary" disabled={loading || busy} onClick={() => void mutate('snapshot')}>Freeze analytical inputs</button>
      <div className="form-field"><label htmlFor="evolution-snapshot">Analytical snapshot</label><select id="evolution-snapshot" value={selectedSnapshot} disabled={loading || busy || !snapshots.items.length} onChange={event => { const value = event.target.value; navigate(() => { clearDrafts(); setSelectedSnapshot(value); }); }}><option value="">No snapshot selected</option>{snapshots.items.map(item => <option value={item.id} key={item.id}>{item.id.slice(0, 12)} · {item.body.sample_sizes.conclusive_reviews} conclusive reviews · {utc(item.created_at)}</option>)}</select></div>
      {!snapshots.items.length && !loading && <p>No analytical snapshots recorded. Freeze existing inputs to inspect the actual sample sizes.</p>}
      {snapshots.next_cursor && <button className="text-button" disabled={busy || loading} onClick={() => void more('snapshots')}>Load more snapshots</button>}
      {snapshot && <><p className="context-warning"><strong>{words(snapshot.body.detector_gate.status)}</strong> · {snapshot.body.detector_gate.conclusive_reviews} / 30 conclusive reviews overall; {snapshot.body.detector_gate.target_rule_reviews} / 15 for High value.</p><dl className="usage-values"><dt>Reviewed alerts</dt><dd>{snapshot.body.sample_sizes.reviewed_alerts}</dd><dt>Inconclusive reviews</dt><dd>{snapshot.body.sample_sizes.inconclusive_reviews}</dd><dt>Feedback revisions retained</dt><dd>{snapshot.body.sample_sizes.feedback_events}</dd><dt>Label provenance</dt><dd>{words(snapshot.body.label_provenance)}</dd><dt>Population recall / false-positive rate</dt><dd>Unavailable from reviewed alerts</dd></dl><p className="muted">Only the latest verdict per alert counts. Source labels and model suggestions are not human reviews.</p><details><summary>Snapshot usage</summary><UsageDisplay usage={snapshot.body.usage} /></details></>}
      <button className="primary" disabled={busy || loading || !canRun || !snapshot?.body.sample_sizes.feedback_events} onClick={() => setConfirm('a5')}>Queue Evolution analysis</button><p className="muted">{!snapshot?.body.sample_sizes.feedback_events ? 'Record genuine analyst feedback against a completed investigation before A5.' : !canRun ? 'Verified local free-tier access or credited cloud access is required before a model call.' : 'One A5 attempt per frozen snapshot. Today’s separate admin switch and attempt cap still apply.'}</p>
    </section>
    <section className="panel"><h3>Evolution analysis history</h3><div className="form-field"><label htmlFor="evolution-run">Stored analysis</label><select id="evolution-run" value={selectedRun} disabled={busy || loading || !runs.items.length} onChange={event => { const value = event.target.value; navigate(() => { clearDrafts(); setSelectedRun(value); }); }}><option value="">No analysis selected</option>{runs.items.map(run => <option key={run.id} value={run.id}>{run.id.slice(0, 12)} · {words(run.state)}</option>)}</select></div>
      {!runs.items.length && !loading && <p>No A5 analysis recorded. No proposal or improvement has been established.</p>}{runs.next_cursor && <button className="text-button" disabled={busy || loading} onClick={() => void more('runs')}>Load more analyses</button>}
      {detailLoading && <p role="status">Loading stored analysis…</p>}{detail && <><p>Analysis: {words(detail.run.state)}{detail.run.error_code && ` · ${detail.run.error_code}`}</p><button className="text-button" onClick={() => onRun(detail.run.id)}>View analysis usage</button><p className="evidence-id">Snapshot: {detail.analytical_snapshot_id}</p>{detail.result && <><h4>{words(detail.result.status)}</h4><p>{detail.result.conclusive_reviews} conclusive reviews overall · {detail.result.target_rule_reviews} target-rule reviews</p><ul>{detail.result.limitations.map((text, index) => <li key={index}>{text}</li>)}</ul></>}
        {detail.recommendation?.diff ? <><h4>Detector recommendation · {words(detail.recommendation.state)}</h4><p>{detail.recommendation.hypothesis}</p><p>{detail.recommendation.diff.rule_id}: {detail.recommendation.diff.before} → {detail.recommendation.diff.after.id}</p><p className="muted">Review records your assessment. It never activates the candidate.</p>{detail.recommendation.review_notes && <p>Saved review: {detail.recommendation.review_notes}</p>}<form noValidate onSubmit={review}><div className="form-field"><label htmlFor="proposal-state">Review decision</label><select id="proposal-state" value={reviewState} disabled={busy} onChange={event => setReviewState(event.target.value)}><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option></select></div><div className="form-field"><label htmlFor="proposal-notes">Recommendation review notes</label><textarea className="resize-none" ref={reviewRef} id="proposal-notes" rows={5} maxLength={2000} value={reviewNotes} disabled={busy} aria-invalid={fieldError === 'review'} aria-describedby={fieldError === 'review' ? 'proposal-error' : undefined} onChange={event => setReviewNotes(event.target.value)} />{fieldError === 'review' && <span id="proposal-error" className="field-error">Add your review notes.</span>}</div><button className="primary" disabled={busy} aria-busy={busy}>Save recommendation review</button></form></> : <p>No supported detector proposal stored.</p>}
        <p className="muted">{Object.entries(detail.optimization_replays).map(([kind, state]) => `${kind}: ${words(state)}`).join(' · ')}. No optimization gain is claimed.</p></>}
    </section>
    <section className="panel"><h3>Frozen detector comparison</h3>{frozen.freeze ? <><p><strong>{frozen.freeze.candidate.id}</strong> · {words(frozen.freeze.support_status)}</p><p>{frozen.freeze.notes}</p><p className="evidence-id">Candidate hash: {frozen.freeze.candidate_hash}</p><p className="muted">Frozen {utc(frozen.freeze.frozen_at)}. No activation; no reselection from held-out results.</p>{!frozen.simulation && <button className="primary" disabled={busy || loading} onClick={() => setConfirm('simulate')}>Run held-out comparison</button>}
        {frozen.simulation && <p>Stored comparison: {words(frozen.simulation.state)}{frozen.simulation.error_code && ` · ${frozen.simulation.error_code}`}. Refresh to read the stored result; no automatic rerun.</p>}{frozen.simulation?.metrics && <><p>{words(frozen.simulation.metrics.result)} · {frozen.simulation.metrics.case_ids.length} conclusive synthetic held-out cases</p><div className="table-scroll"><table><thead><tr><th>Case metric</th><th>Baseline</th><th>Frozen candidate</th></tr></thead><tbody>{(['TP', 'FP', 'TN', 'FN', 'recall', 'precision', 'fpr'] as const).map(key => <tr key={key}><th scope="row">{key}</th><td>{formatMetric(key, frozen.simulation!.metrics!.baseline[key])}</td><td>{formatMetric(key, frozen.simulation!.metrics!.candidate_metrics[key])}</td></tr>)}</tbody></table></div><dl className="usage-values"><dt>Benign alerts removed</dt><dd>{frozen.simulation.metrics.benign_alerts_removed}</dd><dt>Suspicious alerts removed</dt><dd>{frozen.simulation.metrics.suspicious_alerts_removed}</dd><dt>Cases retained by other rules</dt><dd>{frozen.simulation.metrics.cases_retained_by_other_rules.length}</dd><dt>Additional missed cases</dt><dd>{frozen.simulation.metrics.additional_missed_case_ids.length}</dd><dt>Provenance</dt><dd>{words(frozen.simulation.metrics.provenance)}</dd></dl><p className="muted">Synthetic reference-label replay. These outcomes are not human verdicts or live performance.</p></>}</> : <><p>No candidate frozen. Select an allowlisted detector only after a genuine A5 result. Insufficient feedback remains labeled.</p><form noValidate onSubmit={prepareFreeze}><fieldset disabled={busy || loading || !detail?.result}><div className="form-field"><label htmlFor="freeze-candidate">Detector candidate</label><select id="freeze-candidate" value={candidate} onChange={event => { const value = event.target.value; navigate(() => { setFreezeNotes(''); setCandidate(value); }); }}><option value="">Choose a detector candidate</option>{options.map(item => <option key={item.candidate.id} value={item.candidate.id}>{item.candidate.id} · {words(item.candidate.kind)}</option>)}</select></div>{option && <p className="evidence-id">Candidate hash: {option.candidate_hash}</p>}<div className="form-field"><label htmlFor="freeze-notes">Candidate freeze notes</label><textarea className="resize-none" ref={freezeRef} id="freeze-notes" rows={5} maxLength={2000} value={freezeNotes} aria-invalid={fieldError === 'freeze'} aria-describedby={fieldError === 'freeze' ? 'freeze-error' : undefined} onChange={event => setFreezeNotes(event.target.value)} />{fieldError === 'freeze' && <span id="freeze-error" className="field-error">Explain your candidate selection.</span>}</div><button className="primary" disabled={!option || !detail?.result || busy}>Freeze detector candidate</button></fieldset></form></>}
    </section>
    <RecommendationQueue discardVersion={discardVersion} token={token} onError={onError} onDirty={setRecommendationDirty} navigate={navigate} />
    {confirm && <Dialog title={confirm === 'a5' ? 'Queue Evolution analysis?' : confirm === 'freeze' ? 'Freeze detector candidate?' : 'Open held-out comparison?'} description={confirm === 'a5' ? 'This queues one real A5 model attempt for the selected analytical snapshot. The separate worker checks verified access, today’s switch and cap before sending.' : confirm === 'freeze' ? `Freeze ${candidate} for this dataset. You cannot select another detector after freezing. Insufficient feedback stays labeled; this does not activate a rule or open held-out data.` : `Evaluate the frozen ${frozen.freeze?.candidate.id} once against synthetic held-out labels. The result will be stored and must not guide further tuning.`} onClose={() => setConfirm(null)}><div className="dialog-actions"><button className="text-button" onClick={() => setConfirm(null)}>Keep reviewing</button><button className="primary" onClick={() => void mutate(confirm)}>{confirm === 'a5' ? 'Queue Evolution analysis' : confirm === 'freeze' ? 'Freeze detector candidate' : 'Run held-out comparison'}</button></div></Dialog>}
  </div>;
}

function formatMetric(key: string, value: number | null) {
  if (value === null) return 'Unavailable';
  return ['recall', 'precision', 'fpr'].includes(key)
    ? new Intl.NumberFormat('en-AU', { style: 'percent', maximumFractionDigits: 1 }).format(value)
    : value.toLocaleString('en-AU');
}
