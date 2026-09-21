import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { Stat, Prov, VideoDemo } from '../components/ui';

const INDEX: Array<[string, string, string, string]> = [
  ['01', 'Global Map', 'Real cells, live satellites, density and incidents.', '#/map'],
  ['02', 'Operations AI', 'Anomaly, prediction, handoff, what-if and copilot.', '#/ops'],
  ['03', 'Topology', 'Devices, cells, satellites and ground stations.', '#/topology'],
  ['04', 'Data & Methodology', 'What is real, derived, simulated and predicted.', '#/sources'],
  ['05', 'Guided Tour', 'The full story in three automatic minutes.', '#/tour'],
];

export function Home() {
  const [h, setH] = useState<any>(null);
  useEffect(() => { api.health().then(setH).catch(() => {}); }, []);
  return (
    <div>
      <section className="hero" aria-label="Introduction">
        <div className="hero-glow" aria-hidden="true" />
        <p className="mono hero-eyebrow">● Live · Independent engineering research</p>
        <h1 className="hero-title">ORBITIQ</h1>
        <p className="hero-sub">
          AI-powered <span className="accent">satellite-to-cellular</span> network intelligence —
          real data, machine learning, digital twin and optimization in one command center.
        </p>
        <div className="hero-meta">
          <Prov label="REAL" /> <Prov label="DERIVED" /> <Prov label="SIMULATED" />
          <Prov label="PREDICTION" /> <Prov label="AI RECOMMENDATION" />
        </div>
        <div className="hero-cta">
          <a className="btn btn-primary" href="#video">▶ Watch the 90-second demo</a>
          <a className="btn btn-success" href="#/tour">▶ Launch interactive demo</a>
        </div>
        <div className="stat-grid">
          <Stat title="Connected devices" value={h?.connected_devices?.toLocaleString() ?? '…'} prov="SIMULATED" />
          <Stat title="Active satellites" value={String(h?.active_satellites ?? '…')} prov="REAL" />
          <Stat title="Active cells" value={h?.active_cells?.toLocaleString() ?? '…'} prov="REAL" />
          <Stat title="Network health" value={h ? `${h.network_health_pct}%` : '…'} prov="SIMULATED" />
          <Stat title="Predicted incidents" value={String(h?.predicted_incidents ?? '…')} prov="PREDICTION" />
          <Stat title="AI recommendations" value={String(h?.ai_recommendations ?? '…')} prov="AI RECOMMENDATION" />
        </div>
      </section>

      <section className="sec" aria-label="System index">
        <div className="sec-head">
          <span className="sec-bar" aria-hidden="true" />
          <h2 className="sec-title">Command Center</h2>
        </div>
        <ul className="index-list">
          {INDEX.map(([no, name, desc, href]) => (
            <li key={no} className="index-item">
              <a href={href}>
                <span className="index-no">{no}</span>
                <span className="index-name">{name}<span className="index-desc">{desc}</span></span>
                <span className="index-arrow" aria-hidden="true">→</span>
              </a>
            </li>))}
        </ul>
      </section>

      <div className="sec"><VideoDemo /></div>

      <section className="sec" aria-label="Provenance statement">
        <div className="panel quote">
          <p className="quote-text">
            “ORBITIQ is an independent engineering research prototype inspired by the
            technical challenges of satellite-to-cellular connectivity. It uses public
            datasets, derived engineering features, and controlled simulation. It does
            not use proprietary SpaceX data.”
          </p>
          <p className="fine" style={{ margin: 0 }}>
            Cellular infrastructure data: OpenCelliD (CC BY-SA 4.0). Orbital data: CelesTrak.
            Space weather: NOAA SWPC (contextual only).
          </p>
        </div>
      </section>
    </div>
  );
}
