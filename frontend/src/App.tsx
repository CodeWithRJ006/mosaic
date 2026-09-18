import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { wsClient } from './lib/ws';
import ControlTowerScreen from './screens/ControlTowerScreen';
import IncidentScreen from './screens/IncidentScreen';
import RecoveryScreen from './screens/RecoveryScreen';
import DecisionTraceScreen from './screens/DecisionTraceScreen';
import JudgeModeScreen from './screens/JudgeModeScreen';
import AutopsyScreen from './screens/AutopsyScreen';
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
            <Link to="/judge" className="text-amber-400/80 hover:text-amber-400 transition-colors font-semibold">Judge Mode</Link>
          </div>
        </header>
        
        <main className="flex-1 flex flex-col relative">
          <Routes>
            <Route path="/" element={<ControlTowerScreen />} />
            <Route path="/incident/:shipmentId" element={<IncidentScreen />} />
            <Route path="/recovery/:shipmentId" element={<RecoveryScreen />} />
            <Route path="/trace/:shipmentId" element={<DecisionTraceScreen />} />
            <Route path="/judge" element={<JudgeModeScreen />} />
            <Route path="/autopsy/:shipmentId" element={<AutopsyScreen />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
