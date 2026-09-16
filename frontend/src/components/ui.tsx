import React from 'react';

/** Provenance chips — translucent color-coded tags on dark. */
const TAG_CLASS: Record<string, string> = {
  REAL: 'tag tag-green',
  DERIVED: 'tag tag-sky',
  SIMULATED: 'tag tag-amber',
  PREDICTION: 'tag tag-violet',
  'AI RECOMMENDATION': 'tag tag-pink',
  'SIMULATION RESULT': 'tag tag-orange',
};
export function Prov({ label }: { label: string }) {
  const key = label.split(' ')[0];
  return <span className={TAG_CLASS[label] ?? TAG_CLASS[key] ?? 'tag tag-sky'}>[{label}]</span>;
}

const STAT_ACCENT: Record<string, string> = {
  SIMULATED: 'stat-accent-amber',
  REAL: 'stat-accent-green',
  PREDICTION: 'stat-accent-violet',
  'AI RECOMMENDATION': 'stat-accent-pink',
};
export function Stat({ title, value, prov }: { title: string; value: string; prov?: string }) {
  return (
    <div className={`stat ${prov ? STAT_ACCENT[prov] ?? '' : ''}`}>
      <p className="stat-num">{value}</p>
      <p className="stat-label">{title}</p>
      {prov && <Prov label={prov} />}
    </div>
  );
}

export function Header({ onRun, onReset }: { onRun: () => void; onReset: () => void }) {
  return (
    <header className="masthead">
      <div className="masthead-inner">
        <a className="brand" href="#/" aria-label="ORBITIQ home">
          <span className="live-dot" aria-hidden="true" />
          <span className="brand-name">ORBITIQ</span>
          <span className="brand-sub">Satellite-to-Cellular Intelligence</span>
        </a>
        <nav className="nav" aria-label="Primary">
          <a href="#/">Home</a>
          <a href="#/map">Map</a>
          <a href="#/ops">Ops AI</a>
          <a href="#/topology">Topology</a>
          <a href="#/sources">Data</a>
          <a href="#/recruiter">Recruiter Mode</a>
          <button className="btn-success" onClick={onRun}>▶ Run Demo</button>
          <button className="btn-ghost" onClick={onReset}>↺ Reset</button>
        </nav>
      </div>
    </header>
  );
}

export function SectionHead({ title, tags, sub }: { title: string; tags?: string[]; sub?: string }) {
  return (
    <div>
      <div className="sec-head">
        <span className="sec-bar" aria-hidden="true" />
        <h2 className="sec-title">{title}</h2>
        {tags?.map(t => <Prov key={t} label={t} />)}
      </div>
      {sub && <p className="fine" style={{ margin: '6px 0 0' }}>{sub}</p>}
    </div>
  );
}

export function VideoDemo() {
  return (
    <section id="video" aria-label="Demo video">
      <SectionHead title="Watch the 90-Second Demo" sub="Real Data · AI/ML · Digital Twin · Network Optimization · GenAI" />
      <div className="video-frame">
        <video controls preload="metadata" poster="/video/thumbnail.png">
          <source src="/video/orbitIQ-demo.mp4" type="video/mp4" />
          <source src="/video/orbitIQ-demo.webm" type="video/webm" />
          <track kind="captions" src="/video/orbitIQ-demo.vtt" label="English" default />
          Demo video unavailable — Launch Interactive Demo.
        </video>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="foot">
      <div className="wrap">
        <div className="foot-grid">
          <div>
            <p className="foot-brand">ORBITIQ</p>
            <p className="fine">
              Independent engineering research prototype inspired by the technical
              challenges of satellite-to-cellular connectivity. It does not use
              proprietary SpaceX data.
            </p>
          </div>
          <div>
            <h4>Data</h4>
            <p className="fine">
              Cellular infrastructure: OpenCelliD (CC&nbsp;BY-SA&nbsp;4.0).
              Orbital data: CelesTrak. Space weather: NOAA SWPC (contextual only).
            </p>
          </div>
          <div>
            <h4>System</h4>
            <p className="fine">
              Python · FastAPI · React · MapLibre · scikit-learn · Docker.
              Deterministic demo · SIMULATION_SEED=42.
            </p>
          </div>
        </div>
        <div className="foot-bottom mono">
          <span>ORBITIQ · Live digital twin</span>
          <span>Real Data · AI/ML · Digital Twin · Optimization · GenAI</span>
        </div>
      </div>
    </footer>
  );
}
