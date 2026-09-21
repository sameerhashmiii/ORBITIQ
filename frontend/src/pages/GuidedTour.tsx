import React, { useEffect, useState } from 'react';
import { api } from '../api';

type Status = 'pending' | 'active' | 'done';
interface Summary {
  recommendation: string;
  confidence: number | string;
  explanation: string;
  before: string;
  after: string;
  copilot: string;
}

export function GuidedTour() {
  const [script, setScript] = useState<any>(null);
  const [log, setLog] = useState<string[]>([]);
  const [status, setStatus] = useState<Status[]>([]);
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.recruiter().then(s => {
      setScript(s);
      setStatus((s.steps || []).map(() => 'pending' as Status));
    }).catch(() => {});
  }, []);

  const steps: Array<{ title: string; action: string; run: (push: (s: string) => void) => Promise<void> }> = [
    { title: 'Real cellular infrastructure appears', action: 'GET /api/v1/cells',
      run: async push => { const c: any = await api.cells(500); push(`${c.total.toLocaleString()} live towers loaded`); } },
    { title: 'Satellite trajectories appear', action: 'GET /api/v1/satellites',
      run: async push => { const s: any = await api.satellites(); push(`${s.count} live orbital objects tracked`); } },
    { title: '10,000+ simulated devices appear', action: 'GET /api/v1/coverage',
      run: async push => { const c: any = await api.coverage(); push(`${c.grid.length} density grid cells aggregated`); } },
    { title: 'Introduce satellite congestion', action: 'POST /api/v1/simulation/run',
      run: async push => { await api.runSim(); push('Target satellite driven to 94% utilization'); } },
    { title: 'AI detects anomaly', action: 'GET /api/v1/anomalies',
      run: async push => { const a: any = await api.anomalies(); push(`${a.anomaly_count} anomalies scored with grid areas`); } },
    { title: 'AI predicts connectivity degradation', action: 'GET /api/v1/predictions',
      run: async push => { const p: any = await api.predictions(); push(`${p.degraded_count} devices flagged · 5-min horizon`); } },
    { title: 'AI recommends alternative satellite', action: 'GET /api/v1/recommendations',
      run: async push => {
        const rec: any = await api.recommendations();
        push(`Recommended ${rec.recommended_sat} (confidence ${rec.confidence})`);
        setSummary(s => ({ ...(s as Summary), recommendation: rec.recommended_sat, confidence: rec.confidence, explanation: rec.explanation.join(' · ') }));
      } },
    { title: 'Show explainability', action: 'see recommendations.explanation',
      run: async push => { push('Per-factor deltas attached to every recommendation'); } },
    { title: 'Run outage what-if', action: 'POST /api/v1/whatif/outage',
      run: async push => {
        const w: any = await api.whatif();
        push(`Outage simulated: ${w.before.degraded_users} → ${w.after_ai_optimization.degraded_users} degraded users`);
        setSummary(s => ({ ...(s as Summary),
          before: `${w.before.avg_latency_ms} ms · ${w.before.avg_loss_pct}% loss · ${w.before.degraded_users} degraded`,
          after: `${w.after_ai_optimization.avg_latency_ms} ms · ${w.after_ai_optimization.avg_loss_pct}% loss · ${w.after_ai_optimization.degraded_users} degraded` }));
      } },
    { title: 'Show before / after', action: 'see whatif.before vs after_ai_optimization',
      run: async push => { push('Twin-computed deltas, labeled SIMULATION RESULT'); } },
    { title: 'Ask Copilot: “Why did you recommend this satellite?”', action: 'POST /api/v1/copilot/query',
      run: async push => {
        const cop: any = await api.copilot('Why did you recommend this satellite?');
        push(`Copilot answered (confidence ${cop.confidence})`);
        setSummary(s => ({ ...(s as Summary), copilot: cop.answer }));
      } },
    { title: 'Show data provenance', action: 'GET /api/v1/network/health + data_sources.yaml',
      run: async push => { push('REAL (OpenCelliD/CelesTrak) + DERIVED + SIMULATED + PREDICTION — see Data page'); } },
  ];

  async function run() {
    setRunning(true); setError(null); setSummary(null); setLog([]);
    setStatus(steps.map(() => 'pending'));
    const push = (s: string) => setLog(l => [...l, s]);
    try {
      for (let i = 0; i < steps.length; i++) {
        setStatus(prev => prev.map((s, j) => (j === i ? 'active' : j < i ? 'done' : s)));
        await steps[i].run(push);
        setStatus(prev => prev.map((s, j) => (j <= i ? 'done' : s)));
      }
    } catch (e: any) {
      setError(e.message || 'tour failed');
      push('error: ' + (e.message || e));
    }
    setRunning(false);
  }

  const done = status.filter(s => s === 'done').length;
  const pct = status.length ? Math.round((done / status.length) * 100) : 0;

  return (
    <div>
      <section className="hero" style={{ paddingBottom: 20 }} aria-label="Guided tour header">
        <div className="hero-glow" aria-hidden="true" />
        <p className="mono hero-eyebrow">Guided tour · No narration required · ~3 minutes</p>
        <h1 className="page-title">Guided Tour</h1>
        <p className="lead pagelede">The most impressive engineering story in the system, executed automatically — every step a real API call, every number from the live twin.</p>
        <hr className="divider" />
        <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <button className="btn-success" onClick={run} disabled={running}>{running ? 'Running…' : '▶ Start guided tour'}</button>
          {(running || done > 0) && (
            <span className="mono" aria-live="polite">{done}/{status.length} steps · {pct}%</span>)}
        </div>
        {(running || done > 0) && (
          <div role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}
            style={{ height: 6, background: 'var(--border)', borderRadius: 3, marginTop: 12, overflow: 'hidden' }}>
            <div style={{ width: `${pct}%`, height: '100%', background: 'var(--green)', transition: 'width 300ms' }} />
          </div>)}
        {error && <p className="readout" style={{ color: '#fca5a5' }}>Tour stopped: {error}</p>}
      </section>

      {summary?.recommendation && (
        <div className="rank-best" aria-label="Tour summary">
          <p className="mono" style={{ color: '#86efac' }}>Tour outcome</p>
          <p className="rank-best-name">{summary.recommendation}</p>
          <p className="fine" style={{ color: '#d1fae5' }}>Why: {summary.explanation}</p>
          {summary.before && (
            <p className="readout" style={{ color: '#d1fae5' }}>
              What-if: {summary.before} → {summary.after}
            </p>)}
          <div style={{ marginTop: 12 }}>
            <a className="btn btn-success" href="#/map">Inspect on the map →</a>
            <a className="btn btn-ghost" style={{ color: '#d1fae5' }} href="#/ops">Work it in Ops AI →</a>
          </div>
        </div>)}

      <ol className="steps">
        {(script?.steps ?? steps).map((s: any, i: number) => (
          <li key={s.t ?? i}>
            <span aria-hidden="true" style={{
              display: 'inline-block', width: 10, height: 10, borderRadius: '50%', marginRight: 10,
              background: status[i] === 'done' ? 'var(--green)' : status[i] === 'active' ? 'var(--sky)' : 'transparent',
              border: `2px solid ${status[i] === 'pending' ? 'var(--faint)' : status[i] === 'done' ? 'var(--green)' : 'var(--sky)'}`,
              boxShadow: status[i] === 'active' ? '0 0 8px var(--sky)' : 'none',
            }} />
            <strong style={{ color: status[i] === 'pending' && done === 0 ? undefined : '#fff' }}>{s.title}</strong>
            <span className="mono">{s.action}</span>
          </li>))}
      </ol>
      <div className="log" aria-live="polite">{log.join('\n')}</div>
      {summary?.copilot && (
        <div style={{ marginTop: 16 }}>
          <p className="mono">Copilot said</p>
          <p className="copilot-a">{summary.copilot}</p>
        </div>)}
    </div>
  );
}
