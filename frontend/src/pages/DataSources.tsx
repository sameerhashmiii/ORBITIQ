import React from 'react';
import { Prov } from '../components/ui';
const ROWS: Array<[string, string, string]> = [
  ['OpenCelliD cell sites', 'REAL', 'Live towers via API key (cached), snapshot fallback; CC BY-SA 4.0.'],
  ['CelesTrak TLE / SGP4 positions', 'REAL', 'Live public orbital elements, refreshed when online; snapshot fallback.'],
  ['Elevation / azimuth / slant range / visibility', 'DERIVED', 'Geometry engine (documented simplification).'],
  ['Device telemetry (RSRP, latency, loss, …)', 'SIMULATED', 'Deterministic simulator, SIMULATION_SEED=42.'],
  ['Degradation probability / anomaly score', 'PREDICTION', 'RandomForest + IsolationForest, evaluated (see ml/evaluation).'],
  ['Handoff ranking + what-if deltas', 'AI RECOMMENDATION', 'Transparent weighted scorer + twin rerun.'],
  ['NOAA space weather', 'REAL', 'Displayed only; never claimed to predict performance.'],
];
export function DataSources() {
  return (
    <div>
      <section className="hero" style={{ paddingBottom: 20 }} aria-label="Data header">
        <div className="hero-glow" aria-hidden="true" />
        <p className="mono hero-eyebrow">Provenance · Every pixel declares its origin</p>
        <h1 className="page-title">Data & Methodology</h1>
        <p className="lead pagelede">What is real. What is derived. What is simulated. What the models predict. What the AI recommends.</p>
        <hr className="divider" />
      </section>
      <div className="dtable-wrap">
        <table className="dtable">
          <thead><tr><th scope="col">Data</th><th scope="col">Class</th><th scope="col">Methodology</th></tr></thead>
          <tbody>{ROWS.map(([d, c, m]) => (
            <tr key={d}>
              <td><strong style={{ color: '#fff' }}>{d}</strong></td>
              <td data-th="class"><Prov label={c} /></td>
              <td className="fine">{m}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <p className="fine" style={{ marginTop: 16 }}>
        Full registry: <code>data_sources.yaml</code>. Licenses: OpenCelliD CC BY-SA 4.0 ·
        CelesTrak public TLE · NOAA public domain.
      </p>
    </div>
  );
}
