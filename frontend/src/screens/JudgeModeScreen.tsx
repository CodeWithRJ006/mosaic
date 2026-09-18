import { useState } from 'react';
import { api } from '../lib/api';
import { ShieldAlert, Send } from 'lucide-react';

export default function JudgeModeScreen() {
  const [customPayload, setCustomPayload] = useState('{\n  "shipment_id": "S1",\n  "location": "HUB_4"\n}');
  const [customType, setCustomType] = useState('misroute_shipment');
  const [status, setStatus] = useState<string | null>(null);

  const inject = async (type: string, payload: any) => {
    setStatus('Injecting...');
    try {
      await api.injectDisruption(type, payload);
      setStatus(`Success: Injected ${type}`);
    } catch (e: any) {
      setStatus(`Error: ${e.message}`);
    }
    setTimeout(() => setStatus(null), 3000);
  };

  const handleCustom = () => {
    try {
      const payload = JSON.parse(customPayload);
      inject(customType, payload);
    } catch (e) {
      setStatus('Invalid JSON payload');
      setTimeout(() => setStatus(null), 3000);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto w-full h-full flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-3">
          <ShieldAlert className="w-8 h-8 text-amber-400" /> Judge Mode Console
        </h1>
        <p className="text-slate-400 mt-2">Force inject disruptions directly into the live state engine event bus.</p>
      </div>

      <div className="grid grid-cols-2 gap-6 mt-4">
        
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-6">Quick Actions</h2>
          <div className="flex flex-col gap-3">
            <button 
              onClick={() => inject('misroute_shipment', { shipment_id: "SHP_001", location: "HUB_9" })}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded flex justify-between items-center text-sm"
            >
              <span>Misroute Shipment (SHP_001 &rarr; HUB_9)</span>
              <Send className="w-4 h-4 text-slate-500" />
            </button>

            <button 
              onClick={() => inject('delay_vehicle', { vehicle_id: "VEH_002", delay_minutes: 120 })}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded flex justify-between items-center text-sm"
            >
              <span>Delay Vehicle (VEH_002 by 120m)</span>
              <Send className="w-4 h-4 text-slate-500" />
            </button>

            <button 
              onClick={() => inject('close_hub', { hub_id: "HUB_3", duration_hours: 24 })}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded flex justify-between items-center text-sm"
            >
              <span>Close Hub (HUB_3 for 24h)</span>
              <Send className="w-4 h-4 text-slate-500" />
            </button>

            <button 
              onClick={() => inject('reduce_capacity', { hub_id: "HUB_5", capacity_pct: 0.5 })}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded flex justify-between items-center text-sm"
            >
              <span>Reduce Hub Capacity (HUB_5 to 50%)</span>
              <Send className="w-4 h-4 text-slate-500" />
            </button>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 flex flex-col">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-6">Custom Injection</h2>
          
          <div className="flex flex-col gap-4 flex-1">
            <div>
              <label className="text-xs font-semibold text-slate-400 mb-1 block">Disruption Type</label>
              <input 
                type="text" 
                value={customType}
                onChange={e => setCustomType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm font-mono text-white focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex-1 flex flex-col">
              <label className="text-xs font-semibold text-slate-400 mb-1 block">JSON Payload</label>
              <textarea 
                value={customPayload}
                onChange={e => setCustomPayload(e.target.value)}
                className="w-full flex-1 bg-slate-950 border border-slate-800 rounded p-2 text-sm font-mono text-emerald-400 focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>
            <button 
              onClick={handleCustom}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2 rounded transition-colors"
            >
              Inject Custom Disruption
            </button>
          </div>
        </div>

      </div>
      
      {status && (
        <div className="fixed bottom-8 right-8 bg-slate-800 border border-slate-700 text-white px-6 py-3 rounded-lg shadow-2xl">
          {status}
        </div>
      )}

    </div>
  );
}
