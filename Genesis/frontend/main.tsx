import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type { CaseRecord, Evaluation, Transaction, RunDetail, PrivateAlert } from './types';
import './style.css';
import { Icon } from './Icon';
import { WorkflowExplainer } from './WorkflowExplainer';
import { request } from './api';
import { OperatorReview } from './OperatorReview';
import { Dialog } from './Dialog';
import { CompletionToast, PublicUsage, RunUsageDialog, TOAST_DISMISS_MS } from './Usage';
import { Admin } from './Admin';
import { Evolution } from './Evolution';
import { PublicEvolution } from './RuleIntelligence';
import { ReviewOverview } from './ReviewOverview';
import type { GoogleSignIn } from './google-auth';

const money = (minor: number) => new Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 }).format(minor / 100);
const words = (value: string) => value.toLowerCase().replaceAll('_', ' ');
const date = (value: string) => new Date(value).toLocaleString('en-AU', { timeZone: 'UTC', dateStyle: 'medium', timeStyle: 'short' });


function App() {
  const [runVersion, setRunVersion] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<(() => void) | null>(null);
  const [runId, setRunId] = useState('');
  const [completion, setCompletion] = useState<RunDetail | null>(null);
  useEffect(() => {
    if (!completion) return;
    const timeout = window.setTimeout(() => setCompletion(null), TOAST_DISMISS_MS);
    return () => window.clearTimeout(timeout);
  }, [completion?.id]);
  const announced = React.useRef(new Set<string>());
  const [session, setSession] = useState<{ is_admin: boolean; live_ai_eligible: boolean } | null>(null);
  function navigate(action: () => void) { if (dirty) setPendingNavigation(() => action); else action(); }
  useEffect(() => {
    if (!dirty) return;
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', guard);
    return () => window.removeEventListener('beforeunload', guard);
  }, [dirty]);
  const [screen, setScreen] = useState('Investigations');
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [policyVersion, setPolicyVersion] = useState('detector-v1');
  const [autoLabelVersion, setAutoLabelVersion] = useState('auto-label-v1');
  const [queueScope, setQueueScope] = useState('demo');
  const [matrixRule, setMatrixRule] = useState('HIGH_VALUE');
  const [returnRule, setReturnRule] = useState('');
  const [targetAlert, setTargetAlert] = useState('');
  const [selected, setSelected] = useState('');
  const [filter, setFilter] = useState('');
  const [identityType, setIdentityType] = useState('');
  const [identity, setIdentity] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState('');
  const [signIn, setSignIn] = useState(false);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [roles, setRoles] = useState<{ id: number; name: string; kind: string; output: string; used_by: string }[]>([]);
  const [busy, setBusy] = useState<'diagnostic' | 'triage' | null>(null);
  const searchRef = React.useRef<HTMLInputElement>(null);
  const tokenRef = React.useRef(token);
  tokenRef.current = token;
  useEffect(() => {
    setSession(null); setRunId(''); setCompletion(null); announced.current.clear();
    if (!token) { setQueueScope('demo'); setReturnRule(''); setTargetAlert(''); if (screen === 'Admin') setScreen('Investigations'); return; }
    const controller = new AbortController();
    request<{ is_admin: boolean; live_ai_eligible: boolean }>('/api/operator/session', token, { signal: controller.signal }).then(value => { if (!controller.signal.aborted) { setSession(value); setError(previous => previous.startsWith('Your operator session expired.') ? '' : previous); } }).catch(error => { if (!controller.signal.aborted) showError(error); });
    return () => controller.abort();
  }, [token]);
  function announceRun(run: RunDetail) {
    if (run.initiated_by_me && ['COMPLETE', 'FAILED', 'DISPATCH_FAILED'].includes(run.state) && !announced.current.has(run.id)) {
      announced.current.add(run.id); setCompletion(run); setRunVersion(value => value + 1);
    }
  }
  const screens = ['Investigations', 'Evolution lab', 'System design', ...(token ? ['Admin'] : [])];
  const current = cases.find(c => c.id === selected);
  const relevantAlerts = current?.alerts.filter(alert => alert.applicable !== false || alert.frozen || ['QUEUED', 'RUNNING'].includes(alert.status)) || [];
  const triageDone = relevantAlerts.length > 0 && relevantAlerts.every(alert => alert.status === 'COMPLETE' || alert.frozen);
  const reviewDone = relevantAlerts.length > 0 && relevantAlerts.every(alert => alert.frozen);
  function updateAlert(alert: PrivateAlert['alert']) {
    setCases(previous => previous.map(c => {
      if (!c.alerts.some(item => item.id === alert.id)) return c;
      const alerts = c.alerts.map(item => item.id === alert.id ? { ...item, status: alert.status,
        frozen: alert.feedback_revision > 0, actionable: alert.feedback_revision === 0 && item.applicable !== false } : item);
      const pending = alerts.filter(item => !item.frozen && item.applicable !== false);
      return { ...c, alerts, progress: { frozen: alerts.filter(item => item.frozen).length,
        excluded: alerts.filter(item => !item.frozen && item.applicable === false).length,
        awaiting_review: pending.filter(item => item.status === 'COMPLETE').length,
        in_progress: pending.filter(item => ['QUEUED', 'RUNNING'].includes(item.status)).length,
        awaiting_triage: pending.filter(item => !['COMPLETE', 'QUEUED', 'RUNNING'].includes(item.status)).length } };
    }));
  }
  function queueMatches(c: CaseRecord, query: string, type: string, id: string) {
    return (!type || c.evidence.customer.customer_type === type) && (!id || c.evidence.customer.id === id)
      && `${c.name} ${words(c.scenario_family)} ${c.evidence.signals.join(' ')}`.toLowerCase().includes(query.toLowerCase());
  }
  const filteredCases = cases.filter(c => queueMatches(c, filter, identityType, identity));
  const identities = [...new Map(cases.filter(c => !identityType || c.evidence.customer.customer_type === identityType).map(c => [c.evidence.customer.id, c.evidence.customer])).values()];
  function changeQueue(query: string, type: string, id: string) {
    const matches = cases.filter(c => queueMatches(c, query, type, id));
    navigate(() => { setFilter(query); setIdentityType(type); setIdentity(id); if (!matches.some(c => c.id === selected)) setSelected(matches[0]?.id || ''); });
  }
  function clearSearch() { changeQueue('', identityType, identity); searchRef.current?.focus(); }
  function showError(error: unknown) {
    if (tokenRef.current !== token) return;
    if ((error as { status?: number }).status === 401) { setToken(''); setEvaluation(null); setError('Your operator session expired. Sign in again to continue.'); }
    else setError(previous => previous.startsWith('Your operator session expired.') ? previous : error instanceof TypeError || (error as Error).name === 'TimeoutError' ? 'Unable to reach the service. Check your connection and retry.' : (error as Error).message);
  }

  async function load(signal?: AbortSignal) {
    setLoading(true);
    try {
      const data = await request<{ cases: CaseRecord[]; policy_version_id?: string; auto_label_policy_version?: string }>(token ? '/api/operator/cases' + (queueScope === 'discovery' ? '?scope=discovery' : '') : '/api/demo/alerts', token, { signal });
      if (signal?.aborted) return;
      setCases(data.cases); setPolicyVersion(data.policy_version_id || 'detector-v1'); setAutoLabelVersion(data.auto_label_policy_version || 'auto-label-v1');
      setError(previous => previous.startsWith('Your operator session expired.') ? previous : '');
      const matching = data.cases.filter(c => queueMatches(c, filter, identityType, identity));
      setSelected(previous => matching.some(c => c.id === previous) ? previous : matching[0]?.id || '');
    } catch (e) { if (!signal?.aborted) showError(e); } finally { if (!signal?.aborted) setLoading(false); }
  }
  useEffect(() => { const controller = new AbortController(); setCases([]); void load(controller.signal); request<{ roles: typeof roles }>('/api/system/agents', '', { signal: controller.signal }).then(data => setRoles(data.roles)).catch(e => { if (!controller.signal.aborted) showError(e); }); return () => controller.abort(); }, [token, queueScope]);
  useEffect(() => {
    if (!token || !runVersion) return;
    const controller = new AbortController();
    request<{ cases: CaseRecord[] }>(`/api/operator/cases${queueScope === 'discovery' ? '?scope=discovery' : ''}`, token, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setCases(data.cases); })
      .catch(error => { if (!controller.signal.aborted) showError(error); });
    return () => controller.abort();
  }, [runVersion, token, queueScope]);
  function openSupportingCase(caseId: string, alertId: string, ruleId: string) {
    navigate(() => { void request<CaseRecord>(`/api/operator/cases/${caseId}`, token).then(value => {
      if (tokenRef.current !== token) return;
      setMatrixRule(ruleId); setReturnRule(ruleId); setTargetAlert(alertId);
      setFilter(''); setIdentity(''); setIdentityType(''); setSelected(caseId);
      setQueueScope(value.split === 'CALIBRATION_DISCOVERY' ? 'discovery' : 'demo'); setScreen('Investigations');
    }).catch(showError); });
  }
  async function evaluate() {
    if (busy) return;
    setError(''); setBusy('diagnostic');
    try { const result = await request<Evaluation>('/api/operator/evaluation', token); if (tokenRef.current === token) setEvaluation(result); } catch (e) { if (tokenRef.current === token) showError(e); } finally { setBusy(null); }
  }
  async function triage() {
    if (busy) return;
    setError(''); setBusy('triage');
    try { const result = await request<RunDetail>('/api/operator/triage-jobs', token, { method: 'POST', body: JSON.stringify({ alert_ids: current?.alerts.filter(a => a.actionable !== false).map(a => a.id), expected_policy_version: policyVersion, expected_auto_label_policy_version: autoLabelVersion }) }); if (tokenRef.current !== token) return; setRunVersion(v => v + 1); announceRun(result); if (result.error_code) setError(result.error_code + (result.usage.provider_attempts === 0 ? ': No model request was sent.' : ': Inspect run details for completed steps and provider outcomes.')); } catch (e) { showError(e); } finally { setBusy(null); }
  }

  return <div className="workspace">
    <aside className="sidebar"><button className="brand" onClick={() => navigate(() => setScreen('Investigations'))}><span className="brand-icon"><Icon name="logo" size={25} /></span><span>AML Insight<small>INVESTIGATION SUITE</small></span></button>
      <div className="workspace-label"><span className="status-dot" /> Synthetic sandbox</div>
      <span className="nav-caption">WORKSPACE</span><nav aria-label="Main navigation" style={{ '--active-row': screens.indexOf(screen) } as React.CSSProperties}><span className="nav-selection" aria-hidden="true" />{screens.map((name, i) => <button aria-label={name} aria-current={screen === name ? 'page' : undefined} className={screen === name ? 'nav-link active' : 'nav-link'} onClick={() => navigate(() => setScreen(name))} key={name}><Icon name={(['investigations', 'evolution', 'system', 'shield'] as const)[i]} /><RollingLabel key={name + (screen === name ? '-selected' : '-idle')} text={name} />{i === 0 && <small aria-hidden="true">{cases.length}</small>}</button>)}</nav>
      <div className="sidebar-note"><Icon name="shield" size={22} /><br /><span className="eyebrow">HUMAN IN THE LOOP</span><p>Intelligence informs.<br />Analysts decide.</p><small>Monitoring changes require explicit approval.</small></div>
      <button className="operator" onClick={() => navigate(() => token ? (setToken(''), setEvaluation(null)) : setSignIn(true))}><span className="avatar">{token ? 'OP' : 'PV'}</span><span>{token ? 'Operator' : 'Public visitor'}<small>{token ? 'Sign out' : 'Read-only · Sign in'}</small></span><Icon name="arrow" size={16} /></button>
    </aside>
    <main><header className="topbar"><span>Workspace <span className="slash">/</span> <strong>{screen}</strong></span><span className="env-badge"><span className="status-dot" /> Local development</span></header>
      <div className="page-heading"><div><span className="eyebrow">FINANCIAL CRIME INTELLIGENCE</span><h1>{screen}</h1><p>{screen === 'Investigations' ? 'Review the signals. Follow the evidence. Make an informed decision.' : screen === 'Evolution lab' ? 'Track analyst outcomes by identity, typology and detector category.' : screen === 'Admin' ? 'Inspect measured usage and manage daily AI controls.' : 'Six focused roles. One accountable analyst workflow.'}</p></div><span className="outline-tag">SANDBOX / V0.1</span></div>
      <div className="notice"><span><Icon name="info" size={17} /></span><span><strong>Synthetic demonstration.</strong> Source facts and risk scores are computed. Model suggestions require validation and human review. No real customer data.</span></div>
      {error && <div role="alert" className="error">{error}<button onClick={() => setError('')} aria-label="Dismiss error"><Icon name="close" size={16} /></button></div>}
      {loading ? <div className="empty" role="status"><span className="spinner" />Loading published evidence…</div> : !cases.length ? <div className="empty"><h2>Your workspace is ready for data.</h2><p>Start the Firebase emulators, then run <code>npm run seed</code>.</p><button className="primary" onClick={() => void load()}>Retry connection</button></div> : <>
        {screen === 'Investigations' && returnRule && token && <button className="text-button return-link" onClick={() => navigate(() => { setScreen('Evolution lab'); setReturnRule(''); })}>Return to Evolution / {words(returnRule)}</button>}{screen === 'Investigations' && <div className="metrics"><Metric icon="cases" tone="cases" label={queueScope === "discovery" && token ? "Discovery cases" : "Demonstration cases"} value={String(cases.length)} detail="From 112 fictional case bundles" /><Metric icon="alerts" tone="alerts" label="Rule alerts" value={String(cases.reduce((sum, c) => sum + c.alerts.length, 0))} detail="Nine transparent demo rules" /><Metric icon="shield" tone="protected" label="Protected signals" value={String(cases.filter(c => c.evidence.protected_signals.length).length)} detail="Always visible to the analyst" /><Metric icon="analyst" tone="review" label="Human review" value="Required" detail="No automated verdicts" /></div>}
        {screen === 'Investigations' && <div className="investigation-layout"><section className="panel case-list"><div className="panel-heading"><h2><span aria-hidden="true">🔎 </span>Investigation queue</h2><span className="count">{cases.length}</span></div>{token && <button className="text-button" onClick={() => navigate(() => void load())}>Refresh investigation queue</button>}<div className="queue-filters">{token && <div className="form-field"><label htmlFor="queue-scope">Investigation dataset</label><select id="queue-scope" value={queueScope} onChange={event => { const value = event.target.value; navigate(() => { setQueueScope(value); setFilter(''); setIdentity(''); setIdentityType(''); setTargetAlert(''); }); }}><option value="demo">Public demo / 12 cases</option><option value="discovery">Private discovery / 40 cases</option></select></div>}<div className="form-field"><label htmlFor="identity-type">Identity type</label><select id="identity-type" value={identityType} onChange={event => changeQueue(filter, event.target.value, '')}><option value="">All identity types</option><option value="INDIVIDUAL">Individuals</option><option value="ORGANIZATION">Organizations</option></select></div><div className="form-field"><label htmlFor="queue-identity">Identity</label><select id="queue-identity" value={identity} onChange={event => changeQueue(filter, identityType, event.target.value)}><option value="">All identities</option>{identities.map(customer => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></div>{(identity || identityType) && <button className="text-button" onClick={() => changeQueue('', '', '')}>Clear filters</button>}</div><label className="search"><Icon name="search" size={16} /><input ref={searchRef} aria-label="Search cases" placeholder="Search names or signals" value={filter} onChange={e => changeQueue(e.target.value, identityType, identity)} />{filter && <button onClick={clearSearch} aria-label="Clear search"><Icon name="close" size={14} /></button>}</label><p className="result-count" role="status">{filteredCases.length} of {cases.length} cases</p><div className="case-items">{!filteredCases.length && <div className="no-results"><strong>No matching cases</strong><p>Try a name or a different signal.</p><button className="text-button" onClick={clearSearch}>Clear search</button></div>}{filteredCases.map(c => <button key={c.id} onClick={() => navigate(() => setSelected(c.id))} aria-pressed={c.id === selected} className={'case-item ' + (c.id === selected ? 'selected' : '')}><div><span className={'tiny-dot ' + (c.evidence.protected_signals.length ? 'amber' : '')} /><strong>{c.name}</strong></div><p>{words(c.evidence.customer.customer_type)} / {words(c.scenario_family)}</p>{c.progress && <small>{c.progress.awaiting_triage} awaiting triage / {c.progress.awaiting_review} awaiting review / {c.progress.frozen} frozen / {c.progress.excluded} excluded</small>}<small className="queue-hint" title={c.queue_reason}>{words(c.queue_priority)}</small><div><span>{money(c.evidence.trigger.amount_aud_minor)}</span><span className={'badge ' + c.risk.tier.toLowerCase()}>{c.risk.tier === 'UNAVAILABLE' ? 'Needs context' : words(c.risk.tier)}</span></div></button>)}</div></section>
          {current && <section className="case-detail"><div className="panel investigation-header"><div className="panel-heading"><span className="eyebrow">CASE · {current.id.slice(0, 8).toUpperCase()}</span><span className="badge neutral">{token && queueScope === "discovery" ? "Private discovery evidence" : "Published evidence"}</span></div><div className="case-summary"><div><h2>{current.name}</h2><p className="case-profile">{current.evidence.customer.profile_context}</p><p className="muted">{words(current.scenario_family)} / {date(current.evidence.trigger.occurred_at)} UTC</p></div><aside className="case-metadata" aria-label="Identity and queue details"><dl><dt>Customer</dt><dd>{words(current.evidence.customer.customer_type)}</dd><dt>Account</dt><dd>{words(current.evidence.account.status)}</dd><dt>Queue hint</dt><dd>{words(current.queue_priority)}</dd></dl><p>{current.queue_reason}</p><details><summary>Identity and account references</summary><dl><dt>Identity</dt><dd><code>{current.evidence.customer.id}</code></dd><dt>Account</dt><dd><code>{current.evidence.account.id}</code></dd></dl></details></aside></div><div className="trigger"><div><small>TRIGGERING MOVEMENT · AUD EQUIVALENT</small><strong>{money(current.evidence.trigger.amount_aud_minor)}</strong></div><span className="outline-tag">{current.evidence.trigger.type}</span></div><div className="signal-list">{current.alerts.map(a => <span key={a.id} className="signal">{a.rule_name}</span>)}{!current.alerts.length && <span className="muted">No detector alert. Unalerted controls remain in evaluation.</span>}</div>{current.evidence.protected_signals.length > 0 && <p className="protected">Protected signals: {current.evidence.protected_signals.map(words).join(', ')}. Analyst attention required regardless of score.</p>}<ol className="workflow-strip case-workflow" aria-label="Case workflow"><li className="workflow-step complete"><span><Icon name="check" size={11} /></span><div><strong>Source evidence</strong><small>Computed</small></div></li><li className={"workflow-step " + (current.risk.overall_score === null ? "" : "complete")}><span>{current.risk.overall_score === null ? "!" : <Icon name="check" size={11} />}</span><div><strong>Risk scoring</strong><small>{current.risk.overall_score === null ? "Needs context" : "Computed"}</small></div></li><li className={'workflow-step ' + (token && triageDone ? 'complete' : '')}><span>{!token ? <Icon name="lock" size={11} /> : triageDone ? <Icon name="check" size={11} /> : '3'}</span><div><strong>AI triage</strong><small>{!token ? 'Operator-only status' : triageDone ? 'Completed' : relevantAlerts.some(a => ['QUEUED', 'RUNNING'].includes(a.status)) ? 'In progress' : relevantAlerts.length ? 'Awaiting investigation' : 'No applicable alerts'}</small></div></li><li className={'workflow-step ' + (token && reviewDone ? 'complete' : '')}><span><Icon name={token && reviewDone ? 'check' : 'lock'} size={11} /></span><div><strong>Analyst review</strong><small>{!token ? 'Operator-only status' : reviewDone ? 'Saved and frozen' : relevantAlerts.some(a => a.status === 'COMPLETE' && !a.frozen) ? 'Ready for review' : 'Requires validated triage'}</small></div></li></ol></div>
            <div className="detail-grid"><section className="panel risk-panel"><div className="panel-heading"><h3>Risk dimensions</h3><span className="small-label">DETERMINISTIC</span></div><div className="score">{current.risk.overall_score === null ? '—' : current.risk.overall_score.toFixed(2)}<span> / 1.00</span></div><p className="muted">Demo heuristic · not a probability</p>{Object.entries(current.risk.dimensions).map(([name, score]) => <div className="risk-row" key={name}><div><span>{words(name)}</span><small>{Math.round(current.risk.weights[name] * 100)}% weight</small><strong>{score === null ? 'N/A' : score.toFixed(2)}</strong></div><div className="track"><span style={{ width: `${(score || 0) * 100}%` }} /></div></div>)}</section><section className="panel context-panel"><div className="panel-heading"><h3>Evidence snapshot</h3><span className="small-label">A1</span></div><dl><dt>30-day transactions</dt><dd>{current.evidence.facts.window_count}</dd><dt>30-day volume</dt><dd>{money(current.evidence.facts.window_volume_aud_minor)}</dd><dt>Cash intensity</dt><dd>{Math.round((current.evidence.facts.cash_ratio || 0) * 100)}%</dd><dt>Currencies observed</dt><dd>{current.evidence.facts.currency_count}</dd><dt>Historical transactions</dt><dd>{current.evidence.history.length}</dd></dl><div className={current.evidence.missing_context.length ? 'context-warning' : 'context-ok'}><strong>{current.evidence.missing_context.length ? 'Context requires attention' : 'Required context available'}</strong><p>{current.evidence.missing_context.join('. ') || 'Source records linked. Narrative support still needs validation after a live AI run.'}</p></div></section></div>
            <section className="panel"><div className="panel-heading"><h3><span aria-hidden="true">🧾 </span>Transaction trail</h3><span className="small-label">{current.evidence.history.length + 1} OF {current.evidence.history.length + 1} RECORDS · UTC</span></div><div className="table-scroll transaction-scroll" tabIndex={0} role="region" aria-label="Transaction trail"><table><thead><tr><th>When</th><th>Movement</th><th>Type</th><th>AUD equivalent</th></tr></thead><tbody>{[current.evidence.trigger, ...[...current.evidence.history].reverse()].map((t: Transaction, i) => <tr key={t.id} id={`transaction-${t.id}`}><td>{date(t.occurred_at)}<small className="evidence-id" title={t.id}>{i === 0 ? "Trigger" : `History ${i}`}</small></td><td>{t.direction === 'CREDIT' ? '↓ Inbound' : '↑ Outbound'}{i === 0 && <small className="trigger-label">Trigger</small>}</td><td>{words(t.type)} · {t.currency}</td><td className="amount">{money(t.amount_aud_minor)}</td></tr>)}</tbody></table></div><details><summary>Inspect source description</summary><p>{current.evidence.trigger.description}</p><small>Untrusted source text; never an instruction to an agent.</small></details></section>
          </section>}
          {current && <section className="investigation-workspace" aria-label="Investigation and review">
            <section className="panel analyst-panel investigation-stage"><div><span className="eyebrow">INVESTIGATE · AI TRIAGE & HUMAN REVIEW</span><h3>Build the investigation brief. {token && triageDone && <span className="stage-complete"><Icon name="check" size={15} /> Completed</span>}</h3><p>{token && triageDone ? 'The investigation is ready below. Review the analysis and save your verdict. Frozen alerts are preserved.' : 'Explain the evidence, inspect AI suggestions, then make your own analyst decision.'}</p></div><button className="primary" disabled={!token || !current.alerts.some(a => a.actionable !== false) || !!busy} aria-busy={busy === "triage"} onClick={triage}>{busy === "triage" ? "Checking…" : "Check live triage"} <Icon name="arrow" size={15} /></button><small>{token ? 'The separate worker checks verified access, the daily switch and the attempt cap.' : 'Operator sign-in required. Public browsing never triggers model calls.'}</small>{token && <small className="muted">Active detector policy: {policyVersion.slice(0, 12)}</small>}</section>
            <OperatorReview initialAlert={targetAlert} key={current.id} current={current} token={token} version={runVersion} onError={showError} onDirty={setDirty} navigate={navigate} onRun={setRunId} onComplete={announceRun} onStatus={updateAlert} />
            <PublicUsage version={runVersion} />
          </section>}</div>}
        {screen === 'Admin' && token && <Admin token={token} isAdmin={!!session?.is_admin} canEnable={!!session?.live_ai_eligible} onError={showError} onRun={setRunId} />}
        {screen === 'Evolution lab' && <>{token ? <Evolution selectedRule={matrixRule} onSelectRule={setMatrixRule} onOpenCase={openSupportingCase} key="operator-evolution" token={token} canRun={!!session?.live_ai_eligible} onError={showError} onDirty={setDirty} navigate={navigate} onRun={setRunId} /> : <PublicEvolution />}{token && <ReviewOverview token={token} onError={showError} />}<section className="panel evolution-intro"><span className="eyebrow">OPERATOR APPROVAL REQUIRED</span><h2>Close the loop, without losing oversight.</h2><p>Immutable analyst feedback and measured usage inform bounded proposals. Each stored result retains its evidence and review state; monitoring changes require human oversight.</p><WorkflowExplainer /></section><div className="detail-grid"><section className="panel"><h3>Separate discovery from proof</h3><p>40 discovery, 20 selection, 40 held-out, and 12 interactive cases. Reference labels never enter triage prompts. Unalerted cases count toward false negatives.</p><button className="primary" disabled={!token || !!busy} aria-busy={busy === "diagnostic"} onClick={evaluate}>{busy === "diagnostic" ? "Running diagnostic…" : "Run discovery diagnostic"}</button><p className="muted">Operator only. Deterministic replay; no model call or held-out inspection.</p></section><section className="panel"><h3>Optimize quality and cost together</h3><p>Capture tokens, retries, latency, evidence support, abstentions, and analyst outcomes for each leg. Compare frozen prompt and context variants on the same cases.</p><p className="muted">Measured usage is available in the investigation workspace. Prompt, context and weight optimization remain unevaluated until a genuine replay is stored. No automatic activation.</p></section></div>{evaluation && <section className="panel"><h3>Discovery replay</h3><p>{evaluation.warning}</p><div className="table-scroll"><table><thead><tr><th>Candidate</th><th>Benign alerts removed</th><th>Suspicious alerts removed</th><th>Retained by other rules</th><th>Case recall before → after</th><th>Outcome</th></tr></thead><tbody>{evaluation.discovery_preview.map(item => <tr key={item.candidate.id}><td>{item.candidate.id}</td><td>{item.benign_alerts_removed}</td><td>{item.suspicious_alerts_removed}</td><td>{item.cases_retained_by_other_rules.length}</td><td>{item.baseline.recall?.toFixed(2)} → {item.candidate_metrics.recall?.toFixed(2)}</td><td>{words(item.result)}</td></tr>)}</tbody></table></div></section>}</>}
        {screen === 'System design' && <><section className="panel"><div className="panel-heading"><h2><span aria-hidden="true">🤖 </span>Six roles. Explicit handovers.</h2><span className="badge neutral">4 Gemini roles · 2 deterministic</span></div><div className="flow">{roles.map(role => <React.Fragment key={role.id}><span>A{role.id}<small>{role.name}</small></span></React.Fragment>)}</div><p className="muted">A5 analyzes a frozen human-feedback snapshot separately from triage. Small samples remain insufficient evidence; all proposals require review.</p><div className="table-scroll"><table><thead><tr><th>Role</th><th>Implementation</th><th>Output</th><th>Used by</th></tr></thead><tbody>{roles.map(role => <tr key={role.id}><td><strong>A{role.id} · {role.name}</strong></td><td>{role.kind}</td><td>{role.output}</td><td>{role.used_by}</td></tr>)}</tbody></table></div></section><div className="detail-grid"><section className="panel"><h3>Firestore is the source of truth</h3><p>Source records → alerts → triage runs → feedback events → evolution runs → recommendations → evaluations. Stable IDs link each step. Append-only application audit events record actors and versions.</p><p className="muted">Browser access to Firestore is denied. All reads and writes go through the API.</p></section><section className="panel"><h3>Published evidence, bounded operations</h3><p>Public visitors read a frozen, synthetic publication. Authenticated operators use server-verified Firebase tokens. Live calls require verified access, daily controls and a separate worker. Public browsing never starts a model request.</p><p className="muted">Local emulators require no cloud billing.</p></section></div></>}
      </>}<footer>AML Insight <span>AI Builder Cup · BFSI prototype</span><span>Synthetic data · Human decisions</span></footer>
    </main>
    {pendingNavigation && <Dialog title="Discard unsaved review?" description="Your review has unsaved changes. Keep editing or discard them before leaving." onClose={() => setPendingNavigation(null)}><div className="dialog-actions"><button className="primary" onClick={() => setPendingNavigation(null)}>Keep editing</button><button className="text-button" onClick={() => { const action = pendingNavigation; setPendingNavigation(null); setDirty(false); action(); }}>Discard changes</button></div></Dialog>}
    {runId && token && <RunUsageDialog runId={runId} token={token} onClose={() => setRunId('')} onError={showError} />}
    {completion && token && <CompletionToast key={completion.id} run={completion} onOpen={() => setRunId(completion.id)} onDismiss={() => setCompletion(null)} />}
    {signIn && <SignIn onClose={() => setSignIn(false)} onToken={value => { setToken(value); setSignIn(false); setError(''); }} />}
  </div>;
}

function RollingLabel({ text }: { text: string }) {
  return <span className="rolling-label" aria-hidden="true">{Array.from(text).map((letter, index) => <span className="rolling-letter" key={index} style={{ '--letter-index': index } as React.CSSProperties}><span className="rolling-letter-track"><span>{letter === ' ' ? '\u00a0' : letter}</span><span className="rolling-letter-copy">{letter === ' ' ? '\u00a0' : letter}</span></span></span>)}</span>;
}

function Metric({ label, value, detail, icon, tone }: { label: string; value: string; detail: string; icon: 'cases' | 'alerts' | 'shield' | 'analyst'; tone: string }) {
  return <div className={'metric metric-' + tone}><div className="metric-heading"><span className="metric-icon"><Icon name={icon} size={23} /></span><span className="metric-label">{label}</span><strong className={value.length > 3 ? 'metric-value word-value' : 'metric-value'}>{value}</strong></div><small>{detail}</small></div>;
}

function SignIn({ onClose, onToken }: { onClose: () => void; onToken: (token: string) => void }) {
  type AuthConfig = { mode: 'local' | 'cloud'; project_id: string; auth_emulator_url: string | null; firebase_web_api_key: string | null };
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [visible, setVisible] = useState(false);
  const [invalid, setInvalid] = useState({ email: '', password: '' });
  const emailRef = React.useRef<HTMLInputElement>(null);
  const passwordRef = React.useRef<HTMLInputElement>(null);
  const controller = React.useRef(new AbortController());
  const google = React.useRef<GoogleSignIn | null>(null);
  const googleError = React.useRef<(error: unknown) => string>(() => 'Google sign-in failed. Try again.');
  const [googleReady, setGoogleReady] = useState(false);
  async function loadConfiguration() {
    setBusy(true); setError(''); setGoogleReady(false);
    try {
      const value = await request<AuthConfig>('/api/config', '', { signal: controller.current.signal });
      if (controller.current.signal.aborted) return;
      setConfig(value);
      if (value.mode === 'local' && value.auth_emulator_url) {
        setEmail('operator@aml-insight.test'); setPassword('local-demo-only');
      } else if (value.mode === 'cloud' && value.firebase_web_api_key && value.project_id) {
        setEmail(''); setPassword('');
        const { prepareGoogleSignIn, googleSignInError } = await import('./google-auth');
        if (controller.current.signal.aborted) return;
        google.current = prepareGoogleSignIn(value.project_id, value.firebase_web_api_key);
        googleError.current = googleSignInError;
        setGoogleReady(true);
      } else {
        setError('Operator sign-in is not configured. Contact the administrator.');
      }
    } catch { if (!controller.current.signal.aborted) setError('Unable to load sign-in. Check your connection and retry.'); }
    finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  useEffect(() => { void loadConfiguration(); return () => { controller.current.abort(); void google.current?.dispose(); }; }, []);
  const ready = !!config && (config.mode === 'local' ? !!config.auth_emulator_url : googleReady);
  async function signInGoogle() {
    if (busy || !ready || !google.current) return;
    setBusy(true); setError('');
    const signal = controller.current.signal;
    try {
      const idToken = await google.current.signIn(signal);
      if (signal.aborted) return;
      await request('/api/operator/session', idToken, { signal });
      if (!signal.aborted) onToken(idToken);
    } catch (failure) {
      if (!signal.aborted) setError(googleError.current(failure));
    } finally { if (!signal.aborted) setBusy(false); }
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault(); if (busy || !ready || config?.mode !== 'local') return;
    const fields = { email: !email.trim() || emailRef.current?.validity.typeMismatch ? 'Enter a valid email address.' : '', password: !password ? 'Enter your password.' : '' };
    setInvalid(fields); setError('');
    if (fields.email || fields.password) { (fields.email ? emailRef : passwordRef).current?.focus(); return; }
    setBusy(true);
    const signal = AbortSignal.any([controller.current.signal, AbortSignal.timeout(15000)]);
    try {
      const endpoint = `${config.auth_emulator_url}/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=emulator-only`;
      const response = await fetch(endpoint, { method: 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: email.trim(), password, returnSecureToken: true }) });
      const body = await response.json();
      if (!response.ok || typeof body.idToken !== 'string' || !body.idToken) throw new Error('Local sign-in failed. Seed the emulator and check your details.');
      await request('/api/operator/session', body.idToken, { signal });
      if (!signal.aborted) { setPassword(''); onToken(body.idToken); }
    } catch (e) { if (!controller.current.signal.aborted) setError(e instanceof TypeError || (e as Error).name === 'TimeoutError' ? 'Unable to reach sign-in. Check your connection and retry.' : (e as Error).message); } finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  return <Dialog title="Operator sign-in" description={config?.mode === 'local' ? 'These fixture credentials work only with the local emulator. No cloud account is used.' : 'Continue with your approved Google account. Operator access is checked after sign-in.'} onClose={onClose}>
    {config?.mode === 'local' ? <form noValidate onSubmit={submit}>
      <div className="form-field"><label htmlFor="operator-email">Email</label><input id="operator-email" ref={emailRef} type="email" autoComplete="username" required disabled={busy || !ready} value={email} aria-invalid={!!invalid.email} aria-describedby={invalid.email ? 'email-error' : undefined} onChange={e => setEmail(e.target.value)} />{invalid.email && <span className="field-error" id="email-error">{invalid.email}</span>}</div>
      <div className="form-field"><label htmlFor="operator-password">Password</label><span className="password-control"><input id="operator-password" ref={passwordRef} type={visible ? 'text' : 'password'} autoComplete="current-password" required disabled={busy || !ready} value={password} aria-invalid={!!invalid.password} aria-describedby={invalid.password ? 'password-error' : undefined} onChange={e => setPassword(e.target.value)} /><button type="button" onClick={() => setVisible(!visible)} aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible}>{visible ? 'Hide' : 'Show'}</button></span>{invalid.password && <span className="field-error" id="password-error">{invalid.password}</span>}</div>
      {error && <p className="error" role="alert">{error}</p>}{!ready && !busy && <button className="text-button" type="button" onClick={() => void loadConfiguration()}>Retry sign-in setup</button>}<button className="primary" disabled={busy || !ready} aria-busy={busy}>{busy ? 'Verifying…' : 'Sign in locally'}</button>
    </form> : <div className="google-signin-flow">
      {error && <p className="error" role="alert">{error}</p>}
      {!ready && !busy && <button className="text-button" onClick={() => void loadConfiguration()}>Retry sign-in setup</button>}
      <button className="google-signin" disabled={busy || !ready} aria-busy={busy} onClick={() => void signInGoogle()}><Icon name="google" size={20} /><span>{busy ? googleReady ? 'Signing in…' : 'Loading sign-in…' : 'Continue with Google'}</span></button>
      <p role="status">{busy && googleReady ? 'Complete sign-in in the Google window, or close this dialog to cancel.' : 'Your operator session stays in this tab and ends when you reload or sign out.'}</p>
    </div>}
  </Dialog>;
}

createRoot(document.getElementById('root')!).render(<App />);
