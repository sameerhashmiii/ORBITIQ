import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { Prov } from '../components/ui';
export function Topology() {
  const [t, setT] = useState<any>(null);
  const [sel, setSel] = useState<any>(null);
  useEffect(() => { api.topology().then(setT).catch(() => {}); }, []);
  if (!t) return <p className="fine">loading topology…</p>;
  const byType: Record<string, any[]> = {};
  t.nodes.forEach((n: any) => { (byType[n.type] = byType[n.type] || []).push(n); });
  const links = t.links.filter((l: any) => l.from === sel?.id || l.to === sel?.id);
  return (
    <div>
      <section className="hero" style={{ paddingBottom: 20 }} aria-label="Topology header">
        <div className="hero-glow" aria-hidden="true" />
        <p className="mono hero-eyebrow">Graph · Sampled for the browser</p>
        <h1 className="page-title">Topology</h1>
        <p className="fine pagelede">
          <Prov label="REAL" /> <Prov label="SIMULATED" /> <Prov label="DERIVED" />
        </p>
        <hr className="divider" />
        <p className="readout" style={{ marginTop: 12 }}>{t.nodes.length} nodes · {t.links.length} relationships</p>
      </section>
      <div className="topo-cols">
        <div>
          {Object.entries(byType).map(([type, nodes]) => (
            <div key={type} className="topo-group">
              <h4>{type} — {nodes.length}</h4>
              <ul>
                {nodes.slice(0, 30).map((n: any) => (
                  <li key={n.id}><button className={sel?.id === n.id ? 'active' : ''} aria-pressed={sel?.id === n.id}
                    onClick={() => setSel(n)} aria-label={`Inspect ${n.id}`}>{n.id} →</button></li>))}
              </ul>
            </div>))}
        </div>
        <div className="inspect" aria-live="polite">
          <p className="mono">Node inspection</p>
          {sel ? (<div>
            <p className="inspect-name">{sel.id}</p>
            <p className="mono">{sel.type}</p>
            <ul className="rank-list">
              {links.slice(0, 20).map((l: any, i: number) => (
                <li key={i}><span>{l.from} —[{l.rel}]→ {l.to}</span></li>))}
            </ul>
          </div>) : <p className="fine">Select a node to inspect its relationships:
            CONNECTED_TO · CAN_HANDOFF_TO · VISIBLE_TO · ROUTES_THROUGH.</p>}
        </div>
      </div>
    </div>
  );
}
