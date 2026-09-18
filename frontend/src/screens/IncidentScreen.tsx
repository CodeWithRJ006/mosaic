import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { Shipment } from '../lib/api';
import { wsClient } from '../lib/ws';
import { ArrowRight, Box, Play } from 'lucide-react';

export default function IncidentScreen() {
  const { shipmentId } = useParams();
  const navigate = useNavigate();
  
  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const loadData = async () => {
    const shipments = await api.getShipments();
    const s = shipments.find(x => x.id === shipmentId);
    if (s) setShipment(s);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    const unsub = wsClient.subscribe((msg) => {
      if (msg.type === 'STATE_UPDATED' && msg.payload.event_payload?.shipment_id === shipmentId) {
        loadData();
      }
    });
    return unsub;
  }, [shipmentId]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await api.generateRecovery(shipmentId!);
      navigate(`/recovery/${shipmentId}`, { state: { receipt: res } });
    } catch (e) {
      console.error(e);
    }
    setGenerating(false);
  };

  if (loading) return <div className="p-8">Loading incident data...</div>;
  if (!shipment) return <div className="p-8">Shipment not found.</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto w-full flex flex-col gap-8 h-full">
      
      <button onClick={() => navigate(-1)} className="text-sm text-slate-400 hover:text-white self-start">
        &larr; Back to Control Tower
      </button>
      
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-lg bg-rose-500/20 flex items-center justify-center border border-rose-500/50">
          <Box className="w-6 h-6 text-rose-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Disruption Detected: {shipment.id}</h1>
          <div className="text-slate-400 flex items-center gap-2 mt-1">
            Status: <span className="text-rose-400 font-semibold">{shipment.status}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
          <h3 className="text-sm font-semibold uppercase text-slate-400 mb-4 tracking-wider">Expected Route</h3>
          <div className="flex items-center gap-4 text-lg">
            <span className="font-mono bg-slate-900 px-3 py-1 rounded border border-slate-700">{shipment.origin}</span>
            <ArrowRight className="w-5 h-5 text-slate-500" />
            <span className="font-mono bg-slate-900 px-3 py-1 rounded border border-slate-700">{shipment.destination}</span>
          </div>
          <div className="mt-6 text-sm">
            <span className="text-slate-400">SLA Deadline:</span> <span className="text-white ml-2">{new Date(shipment.sla_deadline).toLocaleString()}</span>
          </div>
        </div>

        <div className="bg-rose-950/30 rounded-xl p-6 border border-rose-900/50 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 rounded-full -mr-16 -mt-16 blur-xl"></div>
          <h3 className="text-sm font-semibold uppercase text-rose-400 mb-4 tracking-wider">Current Reality</h3>
          <div className="text-sm text-slate-300">
            Shipment physically located at:
          </div>
          <div className="text-2xl font-mono text-rose-400 mt-2 font-bold">
            {shipment.current_location}
          </div>
          <div className="mt-4 text-xs text-rose-300/70 max-w-xs">
            Location diverges from planned path timeline. Hard constraints violation detected.
          </div>
        </div>
      </div>

      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">MOSAIC Recovery Engine</h3>
            <p className="text-sm text-slate-400">Search temporal capacity graph and generate optimization bounds.</p>
          </div>
          <button 
            onClick={handleGenerate}
            disabled={generating}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-400 text-white px-6 py-2 rounded-lg font-semibold flex items-center gap-2 transition-colors shadow-lg shadow-blue-500/20"
          >
            {generating ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Play className="w-4 h-4" />}
            {generating ? 'Running CP-SAT...' : 'Generate Recovery'}
          </button>
        </div>

      </div>

    </div>
  );
}
