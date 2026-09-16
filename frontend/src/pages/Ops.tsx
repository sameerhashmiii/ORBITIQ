import React, { useState } from 'react';
import { api } from '../api';
import { Prov } from '../components/ui';

function OpsSection({ title, tags, children }: {
  title: string; tags?: string[]; children: React.ReactNode;
}) {
  return (
    <section className="ops-sec" aria-label={title}>
      <div className="sec-head">
        <span className="sec-bar" aria-hidden="true" />
        <h2 className="sec-title" style={{ fontSize: 'clamp(1.35rem, 2.6vw, 1.75rem)' }}>{title}</h2>
        {tags?.map(t => <Prov key={t} label={t} />)}
      </div>
      <div style={{ marginTop: 14 }}>{children}</div>
    </section>
  );
}

export function Ops() {
  const [pred, setPred] = useState<any>(null);
  const [anom, setAnom] = useState<any>(null);
  const [rec, setRec] = useState<any>(null);
  const [whatif, setWhatif] = useState<any>(null);
  const [q, setQ] = useState('Why did you recommend this satellite?');
  const [cop, setCop] = useState<any>(null);
  const [inc, setInc] = useState<any>(null);
  return (
    <div>
      <section className="hero" style={{ paddingBottom: 20 }} aria-label="Operations header">
        <div className="hero-glow" aria-hidden="true" />
        <p className="mono hero-eyebrow">Network operations center</p>
        <h1 className="page-title">Operations</h1>
        <p className="lead pagelede">Detect. Predict. Rank. Explain. Every number carries its provenance.</p>
        <hr className="divider" />
      </section>

      <OpsSection title="Incident Timeline">
        <button className="btn-warning" onClick={() => api.runSim().then(() => api.incidents().then(setInc))}>⚠ Inject satellite congestion</button>
        <button className="btn-ghost" onClick={() => api.incidents().then(setInc)}>Refresh</button>
        {inc ? (
          <ul className="event-list">{inc.items?.map((e: any) => (
            <li key={e.event_id} className={e.severity === 'medium' ? 'sev-medium' : e.severity === 'low' ? 'sev-low' : ''}>
              <span className="event-type">{e.type}</span>{' '}
              <span className="mono">[{e.severity}] · {e.timestamp} · {e.affected_devices} devices</span>
              <p className="fine" style={{ margin: '8px 0 0' }}>
                AI diagnosis: {e.root_cause} · Recommended action: <em>{e.recommended_action}</em>
              </p>
            </li>))}
          </ul>
        ) : <p className="fine">No events yet — run the demo.</p>}
      </OpsSection>

      <OpsSection title="AI Predictions" tags={['PREDICTION']}>
        <button className="btn-violet" onClick={() => api.predictions().then(setPred)}>Predict degradation · 5-min horizon</button>
        <button className="btn-violet btn-ghost" style={{ borderStyle: 'solid' }} onClick={() => api.anomalies().then(setAnom)}>Detect anomalies</button>
        {pred && (
          <p className="readout">
            Degraded: <strong>{pred.degraded_count}</strong> / {pred.items.length} sampled devices.
            Top: {pred.items.filter((p: any) => p.probability > 0.5).slice(0, 3).map((p: any) => `${p.device_id} (${p.probability})`).join(', ')}
          </p>)}
        {anom && (
          <p className="readout">Anomalies: <strong>{anom.anomaly_count}</strong> / {anom.items.length} sampled devices.</p>)}
      </OpsSection>

      <OpsSection title="Handoff Optimization" tags={['AI RECOMMENDATION']}>
        <button className="btn-primary" onClick={() => api.recommendations().then(setRec)}>Rank candidate satellites</button>
        {rec && (
          <div>
            <ul className="rank-list">
              {rec.ranked.map((r: any) => <li key={r.sat_id}><span>{r.sat_id}</span><span>{r.score}</span></li>)}
            </ul>
            <div className="rank-best">
              <p className="mono" style={{ color: '#86efac' }}>Recommended · confidence {rec.confidence}</p>
              <p className="rank-best-name">{rec.recommended_sat}</p>
              <p className="fine" style={{ color: '#d1fae5', margin: 0 }}>Why: {rec.explanation.join(' · ')}</p>
            </div>
          </div>)}
      </OpsSection>

      <OpsSection title="What-If Simulation" tags={['SIMULATION RESULT']}>
        <button className="btn-danger" onClick={() => api.whatif('ORBITIQ-DEMO-07').then(setWhatif)}>Simulate SAT outage</button>
        {whatif && (
          <div className="compare" role="group" aria-label="Before and after comparison">
            <div className="compare-cell">
              <p className="mono">Before</p>
              <p className="kpi">{whatif.before.avg_latency_ms} ms</p>
              <p className="readout">{whatif.before.avg_loss_pct}% loss · {whatif.before.degraded_users} degraded</p>
            </div>
            <div className="compare-mid" aria-hidden="true">→</div>
            <div className="compare-cell compare-after">
              <p className="mono" style={{ color: '#86efac' }}>After AI optimization</p>
              <p className="kpi">{whatif.after_ai_optimization.avg_latency_ms} ms</p>
              <p className="readout">{whatif.after_ai_optimization.avg_loss_pct}% loss · {whatif.after_ai_optimization.degraded_users} degraded</p>
              <p className="fine">Alternative: {whatif.recommended}</p>
            </div>
          </div>)}
      </OpsSection>

      <OpsSection title="GenAI Copilot · grounded">
        <div className="queryrow">
          <input value={q} onChange={e => setQ(e.target.value)} aria-label="Copilot question" />
          <button className="btn-primary" onClick={() => api.copilot(q).then(setCop)}>Ask →</button>
        </div>
        {cop && (
          <div>
            <p className="copilot-a">{cop.answer}</p>
            <p className="mono">Confidence {cop.confidence} · Sources: {cop.sources?.join(', ')}</p>
          </div>)}
      </OpsSection>
    </div>
  );
}
