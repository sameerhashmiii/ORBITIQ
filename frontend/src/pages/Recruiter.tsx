import React, { useEffect, useState } from 'react';
import { api } from '../api';
export function Recruiter() {
  const [script, setScript] = useState<any>(null);
  const [log, setLog] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  useEffect(() => { api.recruiter().then(setScript).catch(() => {}); }, []);
  async function run() {
    setRunning(true); setLog([]);
    const push = (s: string) => setLog(l => [...l, s]);
    try {
      push('01 · Real cellular infrastructure appears'); await api.cells(500);
      push('02 · Satellite trajectories appear'); await api.satellites();
      push('03 · 10,000+ simulated devices appear'); await api.coverage();
      push('04 · Introduce satellite congestion'); await api.runSim();
      push('05 · AI detects anomaly'); push(String((await api.anomalies()).anomaly_count) + ' anomalies');
      push('06 · AI predicts degradation'); push(String((await api.predictions()).degraded_count) + ' predicted degraded');
      const rec: any = await api.recommendations();
      push(`07 · AI recommends ${rec.recommended_sat}`);
      push(`08 · Explainability: ${rec.explanation.join(' · ')}`);
      const w: any = await api.whatif();
      push(`09 · Outage what-if: ${w.before.degraded_users} → ${w.after_ai_optimization.degraded_users} degraded users`);
      const cop: any = await api.copilot('Why did you recommend this satellite?');
      push(`10 · Copilot: ${cop.answer}`);
      push('11 · Provenance: REAL (OpenCelliD/CelesTrak) + DERIVED + SIMULATED + PREDICTION — see Data page.');
    } catch (e: any) { push('error: ' + e.message); }
    setRunning(false);
  }
  return (
    <div>
      <section className="hero" style={{ paddingBottom: 20 }} aria-label="Recruiter header">
        <div className="hero-glow" aria-hidden="true" />
        <p className="mono hero-eyebrow">Guided tour · No narration required</p>
        <h1 className="page-title">Recruiter Mode</h1>
        <p className="lead pagelede">The most impressive engineering story, executed automatically in about three minutes.</p>
        <hr className="divider" />
        <div style={{ marginTop: 16 }}>
          <button className="btn-success" onClick={run} disabled={running}>{running ? 'Running…' : '▶ Start recruiter tour'}</button>
        </div>
      </section>
      <ol className="steps">
        {script?.steps?.map((s: any) => (
          <li key={s.t}><strong style={{ color: '#fff' }}>{s.title}</strong><span className="mono">{s.action}</span></li>))}
      </ol>
      <div className="log" aria-live="polite">{log.join('\n')}</div>
    </div>
  );
}
