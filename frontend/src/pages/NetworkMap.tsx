import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { Prov } from '../components/ui';
export function NetworkMap() {
  const ref = useRef<HTMLDivElement>(null);
  const [info, setInfo] = useState('loading…');
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [{ default: maplibregl }, , cells, sats, cov, inc] = await Promise.all([
          import('maplibre-gl'), import('maplibre-gl/dist/maplibre-gl.css'),
          api.cells(800), api.satellites(), api.coverage(), api.incidents(),
        ]);
        if (cancelled || !ref.current) return;
        const map = new maplibregl.Map({
          container: ref.current,
          style: 'https://demotiles.maplibre.org/style.json',
          center: [-122.4194, 37.7749], zoom: 8,
        });
        map.on('load', () => {
          const cellGeo = { type: 'FeatureCollection', features: cells.items.map((c: any) => ({
            type: 'Feature', properties: { id: c.cell_id },
            geometry: { type: 'Point', coordinates: [c.lon, c.lat] } })) };
          map.addSource('cells', { type: 'geojson', data: cellGeo as any });
          map.addLayer({ id: 'cells', type: 'circle', source: 'cells',
            paint: { 'circle-radius': 3, 'circle-color': '#22c55e' } });
          const satGeo = { type: 'FeatureCollection', features: sats.items.map((s: any) => ({
            type: 'Feature', properties: { id: s.sat_id },
            geometry: { type: 'Point', coordinates: [s.lon, s.lat] } })) };
          map.addSource('sats', { type: 'geojson', data: satGeo as any });
          map.addLayer({ id: 'sats', type: 'circle', source: 'sats',
            paint: { 'circle-radius': 6, 'circle-color': '#7dd3fc',
              'circle-stroke-width': 2, 'circle-stroke-color': '#0b1220' } });
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
        });
        setInfo(`${cells.total} cells [REAL] · ${sats.count} satellites [REAL+DERIVED] · ${cov.grid.length} density grid cells [SIMULATED] · ${inc.items?.length ?? 0} active incidents`);
      } catch (e: any) { setInfo(`map unavailable: ${e.message}`); }
    })();
    return () => { cancelled = true; };
  }, []);
  return (
    <div>
      <section className="hero" style={{ paddingBottom: 20 }} aria-label="Map header">
        <div className="hero-glow" aria-hidden="true" />
        <p className="mono hero-eyebrow">Digital twin · Geography</p>
        <h1 className="page-title">Global Map</h1>
        <p className="fine pagelede">
          <Prov label="REAL" /> <Prov label="DERIVED" /> <Prov label="SIMULATED" />
        </p>
        <hr className="divider" />
        <p className="readout" style={{ marginTop: 12 }}>{info}</p>
      </section>
      <div className="map-frame">
        <div ref={ref} className="maplib-wrap" style={{ height: 560, overflow: 'hidden' }} />
      </div>
      <div className="map-legend" aria-label="Map legend">
        <span><i className="sw sw-cell" />Cell site</span>
        <span><i className="sw sw-sat" />Satellite</span>
        <span><i className="sw sw-den" />Device density</span>
        <span><i className="sw sw-inc" />Incident</span>
      </div>
    </div>
  );
}
