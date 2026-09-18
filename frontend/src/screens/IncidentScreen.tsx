import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { Shipment } from '../lib/api';
import { wsClient } from '../lib/ws';
import { ArrowRight, Box, Play, CheckCircle2, XCircle } from 'lucide-react';

export default function IncidentScreen() {
  const { shipmentId } = useParams();
  const navigate = useNavigate();
  
  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [receipt, setReceipt] = useState<any>(null);

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
      setReceipt(res);
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

        {receipt && (
          <div className="mt-4 bg-slate-900 rounded-lg p-6 border border-emerald-900/50">
            <div className="flex items-center gap-3 mb-6">
              {receipt.status === 'NO_FEASIBLE_PIGGYBACK' ? (
                <XCircle className="w-6 h-6 text-rose-500" />
              ) : (
                <CheckCircle2 className="w-6 h-6 text-emerald-500" />
              )}
              <h4 className="text-lg font-bold text-emerald-400">Decision Receipt: {receipt.status}</h4>
            </div>
            
            {receipt.status !== 'NO_FEASIBLE_PIGGYBACK' && (
              <div className="grid grid-cols-2 gap-4 text-sm mb-6">
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Primary Plan ID</span>
                  <span className="font-mono text-blue-400">{receipt.plan_id}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Weight Margin</span>
                  <span className="font-mono text-emerald-400">+{receipt.weight_check_margin} kg</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">Time Margin</span>
                  <span className="font-mono text-emerald-400">+{receipt.time_check_pickup_margin_minutes} min</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-2">
                  <span className="text-slate-400">SLA Margin</span>
                  <span className="font-mono text-emerald-400">+{receipt.delivery_check_sla_margin_minutes} min</span>
                </div>
              </div>
            )}

            <div className="mt-6">
              <h5 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Rejected Candidate Summary</h5>
              <div className="flex flex-wrap gap-2">
                {receipt.rejected_candidates.length === 0 ? (
                  <span className="text-sm text-slate-500">None</span>
                ) : (
                  receipt.rejected_candidates.slice(0, 5).map((rc: any) => (
                    <div key={rc.candidate_id} className="bg-slate-800 text-xs px-2 py-1 rounded border border-slate-700 flex items-center gap-2">
                      <span className="font-mono text-slate-400">{rc.vehicle_id}</span>
                      <span className="text-rose-400/80">{rc.rejection_reason}</span>
                    </div>
                  ))
                )}
                {receipt.rejected_candidates.length > 5 && (
                  <div className="bg-slate-800 text-xs px-2 py-1 rounded border border-slate-700 text-slate-500">
                    +{receipt.rejected_candidates.length - 5} more
                  </div>
                )}
              </div>
            </div>

          </div>
        )}
      </div>

    </div>
  );
}
