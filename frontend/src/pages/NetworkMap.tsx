import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { Prov } from '../components/ui';

type Selection =
  | { kind: 'cell'; data: any }
  | { kind: 'satellite'; data: any }
  | { kind: 'incident'; data: any }
  | null;

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
      <span className="mono">{k}</span>
      <span className="readout" style={{ textAlign: 'right' }}>{v}</span>
    </div>
  );
}

export function NetworkMap() {
  const ref = useRef<HTMLDivElement>(null);
  const [info, setInfo] = useState('loading…');
  const [sel, setSel] = useState<Selection>(null);
  const [sw, setSw] = useState<any>(null);
  const cache = useRef<{ cells: any[]; sats: any[]; inc: any[] }>({ cells: [], sats: [], inc: [] });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [{ default: maplibregl }, , cells, sats, cov, inc, trk] = await Promise.all([
          import('maplibre-gl'), import('maplibre-gl/dist/maplibre-gl.css'),
          api.cells(1500), api.satellites(), api.coverage(), api.incidents(), api.tracks(),
        ]);
        if (cancelled) return;
        cache.current = { cells: cells.items, sats: sats.items, inc: inc.items || [] };
        api.spaceWeather().then(setSw).catch(() => {});
        if (!ref.current) return;
        const map = new maplibregl.Map({
          container: ref.current,
          style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
          center: [-122.4194, 37.7749], zoom: 8,
        });
        map.on('load', () => {
          const cellGeo = { type: 'FeatureCollection', features: cells.items.map((c: any) => ({
            type: 'Feature', properties: { id: c.cell_id, radio: c.radio },
            geometry: { type: 'Point', coordinates: [c.lon, c.lat] } })) };
          map.addSource('cells', {
            type: 'geojson', data: cellGeo as any,
            cluster: true, clusterRadius: 42, clusterMaxZoom: 11,
          });
          map.addLayer({ id: 'clusters', type: 'circle', source: 'cells', filter: ['has', 'point_count'],
            paint: { 'circle-radius': ['step', ['get', 'point_count'], 14, 25, 19, 100, 25],
              'circle-color': '#0f172a', 'circle-stroke-width': 2, 'circle-stroke-color': '#7dd3fc' } });
          map.addLayer({ id: 'cluster-count', type: 'symbol', source: 'cells', filter: ['has', 'point_count'],
            layout: { 'text-field': '{point_count_abbreviated}', 'text-size': 11 },
            paint: { 'text-color': '#7dd3fc' } });
          map.addLayer({ id: 'cells-unclustered', type: 'circle', source: 'cells', filter: ['!', ['has', 'point_count']],
            paint: { 'circle-radius': 4,
              'circle-color': ['match', ['get', 'radio'], 'LTE', '#22c55e', 'NR', '#7dd3fc',
                'UMTS', '#f59e0b', 'GSM', '#94a3b8', 'CDMA', '#fb923c', '#64748b'] } });
          const satGeo = { type: 'FeatureCollection', features: sats.items.map((s: any) => ({
            type: 'Feature', properties: { id: s.sat_id },
            geometry: { type: 'Point', coordinates: [s.lon, s.lat] } })) };
          map.addSource('sats', { type: 'geojson', data: satGeo as any });
          map.addLayer({ id: 'sats', type: 'circle', source: 'sats',
            paint: { 'circle-radius': 6, 'circle-color': '#ffffff',
              'circle-stroke-width': 2, 'circle-stroke-color': '#7dd3fc' } });
          const trackGeo = { type: 'FeatureCollection', features: (trk.tracks || []).map((t: any) => ({
            type: 'Feature', properties: { id: t.sat_id },
            geometry: { type: 'LineString', coordinates: t.path } })) };
          map.addSource('tracks', { type: 'geojson', data: trackGeo as any });
          map.addLayer({ id: 'tracks', type: 'line', source: 'tracks',
            paint: { 'line-color': '#7dd3fc', 'line-width': 1.5, 'line-opacity': 0.45 } });
          const denGeo = { type: 'FeatureCollection', features: cov.grid.map((g: any) => ({
            type: 'Feature', properties: { count: g.count, lat: g.avg_latency_ms },
            geometry: { type: 'Point', coordinates: [g.lon, g.lat] } })) };
          map.addSource('density', { type: 'geojson', data: denGeo as any });
          map.addLayer({ id: 'density', type: 'circle', source: 'density',
            paint: { 'circle-radius': ['interpolate', ['linear'], ['get', 'count'], 1, 3, 200, 14],
              'circle-color': ['interpolate', ['linear'], ['get', 'lat'], 30, '#f59e0b', 100, '#ef4444'],
              'circle-opacity': 0.45 } });
          const incGeo = { type: 'FeatureCollection', features: (inc.items || []).map((e: any) => ({
            type: 'Feature', properties: { id: e.event_id },
            geometry: { type: 'Point', coordinates: [e.location.lon, e.location.lat] } })) };
          map.addSource('incidents', { type: 'geojson', data: incGeo as any });
          map.addLayer({ id: 'incidents', type: 'circle', source: 'incidents',
            paint: { 'circle-radius': 9, 'circle-color': '#ef4444',
              'circle-stroke-width': 2, 'circle-stroke-color': '#fff' } });
          map.on('click', (e: any) => {
            // 8px tolerance box: small tower dots stay clickable
            const tol: any = [[e.point.x - 8, e.point.y - 8], [e.point.x + 8, e.point.y + 8]];
            const feats = map.queryRenderedFeatures(tol, {
              layers: ['incidents', 'sats', 'clusters', 'cells-unclustered'],
            });
            if (!feats.length) { setSel(null); return; }
            const f = feats[0];
            const id = f.properties?.id;
            if (f.layer.id === 'clusters') {
              const src: any = map.getSource('cells');
              src.getClusterExpansionZoom(f.properties?.cluster_id, (err: any, zoom: number) => {
                if (!err) map.easeTo({ center: (f.geometry as any).coordinates, zoom });
              });
              return;
            }
            if (f.layer.id === 'cells-unclustered') {
              const c = cache.current.cells.find((x: any) => x.cell_id === id);
              if (c) setSel({ kind: 'cell', data: c });
            } else if (f.layer.id === 'sats') {
              const s = cache.current.sats.find((x: any) => x.sat_id === id);
              if (s) setSel({ kind: 'satellite', data: s });
            } else {
              const ev = cache.current.inc.find((x: any) => x.event_id === id);
              if (ev) setSel({ kind: 'incident', data: ev });
            }
          });
          map.getCanvas().style.cursor = 'pointer';
        });
        setInfo(`${cells.total} towers [REAL OpenCelliD] · ${sats.count} satellites [REAL CelesTrak + DERIVED] · ${cov.grid.length} density grid cells [SIMULATED] · ${inc.items?.length ?? 0} active incidents — click any marker to inspect`);
      } catch (e: any) { if (!cancelled) setInfo(`map unavailable: ${e.message}`); }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div>
      <section className="hero" style={{ paddingBottom: 20 }} aria-label="Map header">
        <div className="hero-glow" aria-hidden="true" />
        <p className="mono hero-eyebrow">Digital twin · Geography · Live data</p>
        <h1 className="page-title">Global Map</h1>
        <p className="fine pagelede">
          <Prov label="REAL" /> <Prov label="DERIVED" /> <Prov label="SIMULATED" />
        </p>
        <hr className="divider" />
        <p className="readout" style={{ marginTop: 12 }}>{info}</p>
      </section>
      <div className="topo-cols" style={{ gap: 12 }}>
        <div className="map-frame">
          <div ref={ref} className="maplib-wrap" style={{ height: 560, overflow: 'hidden' }} />
        </div>
        <div className="inspect" aria-live="polite">
          <p className="mono">Inspector — click a marker</p>
          {!sel && <p className="fine">Select a tower, satellite, or incident on the map to see its live record.</p>}
          {sel?.kind === 'cell' && (
            <div>
              <p className="inspect-name" style={{ fontSize: '1.1rem' }}>{sel.data.cell_id}</p>
              <p className="mono">Cell tower · OpenCelliD [REAL]</p>
              <KV k="MCC / MNC / TAC" v={`${sel.data.mcc} / ${sel.data.mnc} / ${sel.data.tac}`} />
              <KV k="Radio" v={sel.data.radio} />
              <KV k="Location" v={`${sel.data.lat}, ${sel.data.lon}`} />
              <KV k="Est. range" v={`${sel.data.range_m} m`} />
              <KV k="Samples" v={sel.data.samples} />
            </div>)}
          {sel?.kind === 'satellite' && (
            <div>
              <p className="inspect-name" style={{ fontSize: '1.1rem' }}>{sel.data.sat_id}</p>
              <p className="mono">Orbital object · CelesTrak [REAL] + geometry [DERIVED]</p>
              <KV k="Position" v={`${sel.data.lat}, ${sel.data.lon}`} />
              <KV k="Altitude" v={`${sel.data.altitude_km} km`} />
              <KV k="Elevation / Azimuth" v={`${sel.data.elevation_deg}° / ${sel.data.azimuth_deg}°`} />
              <KV k="Slant range" v={`${sel.data.slant_range_km} km`} />
              <KV k="Visible" v={sel.data.visible ? `yes · ~${sel.data.visibility_duration_min} min` : 'no'} />
              <KV k="Utilization" v={`${sel.data.utilization_pct}%`} />
            </div>)}
          {sel?.kind === 'incident' && (
            <div>
              <p className="inspect-name" style={{ fontSize: '1.1rem' }}>{sel.data.type}</p>
              <p className="mono">[{sel.data.severity}] · {sel.data.affected_devices} devices</p>
              <KV k="Time" v={sel.data.timestamp} />
              <KV k="Root cause" v={sel.data.root_cause} />
              <KV k="Action" v={sel.data.recommended_action} />
              <KV k="Satellites" v={(sel.data.affected_satellites || []).join(', ') || '—'} />
            </div>)}
        </div>
      </div>
      <div className="map-legend" aria-label="Map legend">
        <span><i className="sw" style={{ background: '#22c55e' }} />LTE</span>
        <span><i className="sw" style={{ background: '#7dd3fc' }} />NR / Satellite</span>
        <span><i className="sw" style={{ background: '#f59e0b' }} />UMTS</span>
        <span><i className="sw" style={{ background: '#94a3b8' }} />GSM</span>
        <span><i className="sw" style={{ background: '#fb923c' }} />CDMA</span>
        <span><i className="sw sw-den" />Device density</span>
        <span><i className="sw sw-inc" />Incident</span>
        <span><i className="sw" style={{ background: 'transparent', borderTop: '2px solid #7dd3fc', borderRadius: 0, height: 0, marginTop: 5 }} />Ground track</span>
      </div>
      <div className="panel" style={{ marginTop: 16 }} aria-label="Space weather">
        <div className="sec-head">
          <span className="sec-bar" aria-hidden="true" />
          <h2 className="sec-title" style={{ fontSize: '1.25rem' }}>Space Weather</h2>
          <Prov label="REAL" />
        </div>
        {sw && sw.kp_index !== undefined ? (
          <p className="readout">
            Kp {sw.kp_index} · solar wind {sw.solar_wind_kms} km/s · Bz {sw.bz_gsm_nt} nT · {sw.source}
            <br /><span className="fine">Contextual display only — never used to predict performance.</span>
          </p>
        ) : <p className="fine">Space-weather source unavailable (degraded source, clearly labeled).</p>}
      </div>
    </div>
  );
}
