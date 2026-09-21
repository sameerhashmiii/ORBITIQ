const BASE = '';
async function get<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}
async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}
export const api = {
  health: () => get<any>('/api/v1/network/health'),
  cells: (limit = 500) => get<any>(`/api/v1/cells?limit=${limit}`),
  satellites: () => get<any>('/api/v1/satellites'),
  tracks: () => get<any>('/api/v1/satellites/tracks?minutes=30&step_s=60'),
  coverage: () => get<any>('/api/v1/coverage'),
  incidents: () => get<any>('/api/v1/incidents'),
  predictions: () => get<any>('/api/v1/predictions?limit=200'),
  anomalies: () => get<any>('/api/v1/anomalies?limit=200'),
  recommendations: () => get<any>('/api/v1/recommendations'),
  topology: () => get<any>('/api/v1/network/topology'),
  spaceWeather: () => get<any>('/api/v1/space-weather'),
  whatif: (sat?: string) => post<any>(`/api/v1/whatif/outage${sat ? `?sat_id=${sat}` : ''}`, {}),
  runSim: () => post<any>('/api/v1/simulation/run', { scenario: 'satellite_congestion' }),
  reset: () => post<any>('/api/v1/demo/reset', {}),
  copilot: (q: string) => post<any>('/api/v1/copilot/query', { question: q }),
  recruiter: () => get<any>('/api/v1/demo/recruiter-script'),
};
