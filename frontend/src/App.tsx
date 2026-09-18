import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { wsClient } from './lib/ws';
import ControlTowerScreen from './screens/ControlTowerScreen';
import IncidentScreen from './screens/IncidentScreen';
import { Navigation } from 'lucide-react';

function App() {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    wsClient.connect();
    const unsub = wsClient.subscribe(() => {
      setConnected(true);
    });
    return unsub;
  }, []);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
        <header className="bg-slate-950 border-b border-slate-800 p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-blue-400 font-bold text-xl tracking-tight">
            <Navigation className="w-6 h-6" />
            MOSAIC
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
              Live Feed
            </span>
            <Link to="/" className="text-slate-300 hover:text-white transition-colors">Control Tower</Link>
          </div>
        </header>
        
        <main className="flex-1 flex flex-col">
          <Routes>
            <Route path="/" element={<ControlTowerScreen />} />
            <Route path="/incident/:shipmentId" element={<IncidentScreen />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
