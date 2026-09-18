import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { Activity, Clock, ChevronLeft, ArrowRightLeft } from 'lucide-react';

export default function AutopsyScreen() {
  const { shipmentId } = useParams();
  const navigate = useNavigate();
  
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAutopsy(shipmentId!).then(res => {
      setData(res);
      setLoading(false);
    }).catch(e => {
      setError(e.message);
      setLoading(false);
    });
  }, [shipmentId]);

  if (loading) return <div className="p-8">Extracting telemetry logs...</div>;
  if (error) return <div className="p-8 text-rose-500">Error: {error}</div>;
  if (!data) return <div className="p-8">No autopsy found.</div>;

  return (
    <div className="p-8 max-w-5xl mx-auto w-full h-full flex flex-col gap-6">
      
      <div>
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-slate-400 hover:text-white mb-4">
          <ChevronLeft className="w-4 h-4" /> Back
        </button>
        <h1 className="text-2xl font-bold flex items-center gap-3 text-emerald-400">
          <Activity className="w-8 h-8" /> Network Autopsy: {shipmentId}
        </h1>
        <p className="text-slate-400 mt-2">Historical reconstruction of the incident and counterfactual baseline comparison.</p>
      </div>

      <div className="grid grid-cols-2 gap-6 mt-4">
        
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 flex flex-col shadow-xl">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-emerald-400 mb-6 flex items-center gap-2">
            MOSAIC Recovery Execution
          </h2>
          
          <div className="grid grid-cols-2 gap-4 flex-1">
            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
              <div className="text-xs uppercase text-slate-400 font-semibold mb-1">Final ETA</div>
              <div className="text-lg font-mono text-white">
                {data.actual_plan.eta ? new Date(data.actual_plan.eta).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '--'}
              </div>
            </div>
            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
              <div className="text-xs uppercase text-slate-400 font-semibold mb-1">Total Incr. Cost</div>
              <div className="text-lg font-mono text-white">${data.actual_plan.cost.toFixed(2)}</div>
            </div>
            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
              <div className="text-xs uppercase text-slate-400 font-semibold mb-1">Extra Distance</div>
              <div className="text-lg font-mono text-white">+{data.actual_plan.distance.toFixed(1)} km</div>
            </div>
            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
              <div className="text-xs uppercase text-slate-400 font-semibold mb-1">Transfers Added</div>
              <div className="text-lg font-mono text-white">{data.actual_plan.transfers}</div>
            </div>
          </div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 border-dashed rounded-xl p-6 flex flex-col opacity-80">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-6 flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4" /> Baseline Counterfactual (Nearest Feasible)
          </h2>
          
          {data.baseline_plan ? (
            <div className="grid grid-cols-2 gap-4 flex-1">
              <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-800">
                <div className="text-xs uppercase text-slate-500 font-semibold mb-1">ETA</div>
                <div className="text-lg font-mono text-slate-400">
                  {new Date(data.baseline_plan.eta).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </div>
              </div>
              <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-800">
                <div className="text-xs uppercase text-slate-500 font-semibold mb-1">Total Incr. Cost</div>
                <div className="text-lg font-mono text-slate-400">${data.baseline_plan.cost.toFixed(2)}</div>
              </div>
              <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-800">
                <div className="text-xs uppercase text-slate-500 font-semibold mb-1">Extra Distance</div>
                <div className="text-lg font-mono text-slate-400">+{data.baseline_plan.distance.toFixed(1)} km</div>
              </div>
              <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-800">
                <div className="text-xs uppercase text-slate-500 font-semibold mb-1">Transfers Added</div>
                <div className="text-lg font-mono text-slate-400">{data.baseline_plan.transfers}</div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-600">
              No feasible baseline existed.
            </div>
          )}
        </div>

      </div>

      <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden mt-4">
        <div className="bg-slate-800 border-b border-slate-700 p-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-slate-400" />
          <h3 className="font-semibold text-white">Incident Event Timeline</h3>
        </div>
        
        {data.timeline.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No events found for this incident.</div>
        ) : (
          <div className="p-6">
            <div className="relative border-l border-slate-700 ml-4 space-y-6">
              {data.timeline.map((event: any, idx: number) => (
                <div key={idx} className="relative pl-6">
                  <div className="absolute -left-1.5 top-1.5 w-3 h-3 bg-slate-700 border-2 border-slate-900 rounded-full"></div>
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-4">
                      <span className="font-bold text-blue-400">{event.type}</span>
                      <span className="text-xs font-mono text-slate-500">t={event.state_version}</span>
                      <span className="text-xs text-slate-500">{new Date(event.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="bg-slate-800/50 border border-slate-800 rounded p-3 text-xs font-mono text-slate-400 whitespace-pre-wrap mt-2">
                      {JSON.stringify(event.payload, null, 2)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
