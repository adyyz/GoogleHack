import { useState } from 'react';
import { Icon } from './Icon';

const steps = [
  { title: 'Reviewed cases', tag: 'Human judgment → labeled evidence', description: 'An analyst records a disposition and supporting notes against a completed investigation. These judgments are kept separate from model predictions and synthetic reference labels.', output: 'Adds: a traceable review event linked to the case and triage run.' },
  { title: 'Feedback snapshot', tag: 'Individual reviews → a fixed analysis set', description: 'Eligible review events are grouped into an immutable snapshot. Sample sizes, inconclusive outcomes, rule coverage and missing fields make the limits of that evidence visible.', output: 'Adds: a reproducible input set and measured pattern statistics.' },
  { title: 'Candidate proposal', tag: 'Observed patterns → a bounded suggestion', description: 'Evolution intelligence interprets the statistics and supporting cases, then explains an allowed monitoring change. Prompt or context changes remain proposals for separate quality and cost evaluation.', output: 'Adds: a versioned candidate with rationale, supporting cases and limitations.' },
  { title: 'Independent evaluation', tag: 'A frozen candidate → measured tradeoffs', description: 'After selection is frozen, replay compares baseline and candidate on held-out cases. It counts benign alerts removed, suspicious cases missed and cases retained by other rules.', output: 'Adds: a reproducible impact comparison; zero observed misses is only a sample result.' },
  { title: 'Human review', tag: 'Measured results → an accountable decision', description: 'A monitoring lead inspects the evidence and tradeoffs, then records reviewed or rejected with notes. Only validated, allowlisted detector changes and separately validated A0 cutoffs can be applied through explicit operator approval. Prompts, model choices and risk weights are outside these controls.', output: 'Adds: a recorded decision and an audit trail. No automatic application or deployment.' },
];

export function WorkflowExplainer() {
  const [active, setActive] = useState(0);
  const step = steps[active];
  return <div className="workflow-explainer">
    <div className="explanation-flow" aria-label="Explore the feedback workflow">
      {steps.map((item, index) => <div className={'flow-leg ' + (active === index ? 'is-active' : '')} key={item.title}>
        <button aria-pressed={active === index} aria-controls="workflow-explanation" onPointerEnter={() => setActive(index)} onFocus={() => setActive(index)} onClick={() => setActive(index)}><span className="flow-step-number">{String(index + 1).padStart(2, '0')}</span>{item.title}</button>
        {index < steps.length - 1 && <span className="flow-connector" aria-hidden="true"><Icon name="arrow" size={18} /></span>}
      </div>)}
    </div>
    <section id="workflow-explanation" className="flow-explanation" aria-label="Workflow step explanation">
      <div className="flow-explanation-heading"><span className="explanation-marker">{String(active + 1).padStart(2, '0')}</span><div><h3>{step.title}</h3><span>{step.tag}</span></div><span className="outline-tag">DESIGNED WORKFLOW</span></div>
      <p>{step.description}</p><div className="flow-output"><Icon name="arrow" size={15} /><span>{step.output}</span></div>
    </section>
    <p className="flow-help">Hover, focus, or select a step to explore its handover. This explains the designed workflow; stored evidence and actual results appear separately below.</p>
  </div>;
}
