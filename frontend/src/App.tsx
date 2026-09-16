import React, { useState } from 'react';
import { api } from './api';
import { Header, Footer } from './components/ui';
import { Home } from './pages/Home';
import { NetworkMap } from './pages/NetworkMap';
import { Ops } from './pages/Ops';
import { Topology } from './pages/Topology';
import { DataSources } from './pages/DataSources';
import { Recruiter } from './pages/Recruiter';
export function App() {
  const [route, setRoute] = useState(window.location.hash || '#/');
  const [, force] = useState(0);
  React.useEffect(() => {
    const fn = () => {
      setRoute(window.location.hash || '#/');
      force(x => x + 1);
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', fn);
    return () => window.removeEventListener('hashchange', fn);
  }, []);
  return (
    <div style={{ background: 'var(--bg)', color: 'var(--text)', minHeight: '100vh', fontFamily: 'var(--font-body)' }}>
      <a className="skip" href="#main">Skip to content</a>
      <Header onRun={() => api.runSim().then(() => alert('Demo scenario injected'))}
        onReset={() => api.reset().then(() => alert('Demo reset'))} />
      <main id="main" className="wrap">
        {route.startsWith('#/map') ? <NetworkMap />
          : route.startsWith('#/ops') ? <Ops />
          : route.startsWith('#/topology') ? <Topology />
          : route.startsWith('#/sources') ? <DataSources />
          : route.startsWith('#/recruiter') ? <Recruiter /> : <Home />}
      </main>
      <Footer />
    </div>
  );
}
