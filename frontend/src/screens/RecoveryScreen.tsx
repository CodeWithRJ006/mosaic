import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { CheckCircle2, AlertTriangle, XCircle, BarChart3, ShieldCheck } from 'lucide-react';

export default function RecoveryScreen() {
  const { shipmentId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  
  const receipt = location.state?.receipt;
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    if (!receipt) {
      // shouldn't happen via normal flow, redirect back
      navigate(`/incident/${shipmentId}`);
      return;
    }
    
    // Fetch DB plans to get ETA, cost, transfers, etc.
    api.getPlans(shipmentId!).then(res => {
      setPlans(res);
      setLoading(false);
    });
  }, [receipt, shipmentId, navigate]);

  const primaryPlan = plans.find(p => p.strategy === 'PRIMARY');
  const shadowPlan = plans.find(p => p.strategy === 'SHADOW');

  const handleApprove = async (planId: string) => {
    setApproving(true);
    await api.approvePlan(planId);
    setApproving(false);
    navigate(`/`);
  };

  if (!receipt) return null;
  if (loading) return <div className="p-8">Loading recovery options...</div>;

  const isNoFeasible = receipt.status === 'NO_FEASIBLE_PIGGYBACK';

  // Aggregate rejection reasons
  const rejectionCounts = receipt.rejected_candidates.reduce((acc: any, rc: any) => {
    acc[rc.rejection_reason] = (acc[rc.rejection_reason] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-8 max-w-5xl mx-auto w-full h-full flex flex-col gap-6">
      
      <div className="flex items-center justify-between">
        <div>
          <button onClick={() => navigate(-1)} className="text-sm text-slate-400 hover:text-white">
            &larr; Back to Incident
          </button>
          <h1 className="text-2xl font-bold mt-2">Recovery Plans for {shipmentId}</h1>
        </div>
        {!isNoFeasible && (
          <Link to={`/trace/${shipmentId}`} state={{ receipt }} className="flex items-center gap-2 text-blue-400 hover:text-blue-300 font-semibold bg-blue-900/30 px-4 py-2 rounded-lg border border-blue-800/50">
            <ShieldCheck className="w-5 h-5" /> Decision Trace
          </Link>
        )}
      </div>

      {isNoFeasible ? (
        <div className="bg-rose-950/20 border border-rose-900/50 rounded-xl p-8 flex flex-col items-center justify-center text-center">
          <XCircle className="w-16 h-16 text-rose-500 mb-4" />
          <h2 className="text-2xl font-bold text-rose-400 mb-2">No Feasible Piggyback Found</h2>
          <p className="text-slate-400 max-w-lg mb-8">
            The optimization engine evaluated all candidates but none passed the hard constraint filters. A dedicated recovery vehicle or relaxed SLA is required.
          </p>

          <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-sm font-semibold uppercase text-slate-500 mb-6 flex items-center justify-center gap-2">
              <BarChart3 className="w-4 h-4" /> Rejection Breakdown
            </h3>
            
            <div className="flex flex-col gap-3">
              {Object.entries(rejectionCounts).map(([reason, count]) => {
                const percentage = Math.round((Number(count) / receipt.rejected_candidates.length) * 100);
                return (
                  <div key={reason} className="flex items-center gap-4">
                    <div className="w-48 text-right text-sm text-slate-300 font-mono truncate">{reason}</div>
                    <div className="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full bg-rose-500 rounded-full" style={{ width: `${percentage}%` }}></div>
                    </div>
                    <div className="w-12 text-sm text-slate-400 text-right">{percentage}%</div>
                  </div>
                );
              })}
            </div>
            
            <div className="mt-8 text-center">
              <Link to={`/trace/${shipmentId}`} state={{ receipt }} className="text-blue-400 hover:underline text-sm font-semibold">
                View Full Decision Trace &rarr;
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-6">
          
          {primaryPlan && (
            <div className="bg-slate-800 border-2 border-emerald-500/50 rounded-xl p-6 relative flex flex-col shadow-lg shadow-emerald-500/10">
              <div className="absolute top-0 right-0 bg-emerald-500 text-slate-900 text-xs font-bold px-3 py-1 rounded-bl-lg uppercase tracking-wider">
                Primary Plan
              </div>
              <h2 className="text-xl font-bold mb-6 text-white">Optimal Strategy</h2>
              
              <div className="grid grid-cols-2 gap-4 flex-1">
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-700">
                  <div className="text-xs uppercase text-slate-500 font-semibold mb-1">ETA</div>
                  <div className="text-lg font-mono">{new Date(primaryPlan.eta).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-700">
                  <div className="text-xs uppercase text-slate-500 font-semibold mb-1">SLA Margin</div>
                  <div className="text-lg font-mono text-emerald-400">+{receipt.delivery_check_sla_margin_minutes?.toFixed(1)}m</div>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-700">
                  <div className="text-xs uppercase text-slate-500 font-semibold mb-1">Transfers</div>
                  <div className="text-lg font-mono">{primaryPlan.vehicles.length - 1}</div>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-700">
                  <div className="text-xs uppercase text-slate-500 font-semibold mb-1">Incr. Cost</div>
                  <div className="text-lg font-mono">${primaryPlan.incremental_cost.toFixed(2)}</div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-700 flex justify-between items-center">
                <div className="text-xs text-slate-500 font-mono">{primaryPlan.plan_id}</div>
                <button 
                  disabled={approving}
                  onClick={() => handleApprove(primaryPlan.plan_id)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2 rounded-lg font-semibold flex items-center gap-2 shadow-lg shadow-emerald-500/20 transition-all"
                >
                  <CheckCircle2 className="w-5 h-5" /> {approving ? 'Approving...' : 'Approve Plan'}
                </button>
              </div>
            </div>
          )}

          {shadowPlan ? (
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 relative flex flex-col">
              <div className="absolute top-0 right-0 bg-slate-700 text-slate-300 text-xs font-bold px-3 py-1 rounded-bl-lg uppercase tracking-wider">
                Shadow Plan
              </div>
              <h2 className="text-xl font-bold mb-6 text-slate-300">Fallback Strategy</h2>
              
              <div className="grid grid-cols-2 gap-4 flex-1 opacity-80">
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                  <div className="text-xs uppercase text-slate-600 font-semibold mb-1">ETA</div>
                  <div className="text-lg font-mono text-slate-400">{new Date(shadowPlan.eta).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                  <div className="text-xs uppercase text-slate-600 font-semibold mb-1">SLA Margin</div>
                  <div className="text-lg font-mono text-slate-400">--</div>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                  <div className="text-xs uppercase text-slate-600 font-semibold mb-1">Transfers</div>
                  <div className="text-lg font-mono text-slate-400">{shadowPlan.vehicles.length - 1}</div>
                </div>
                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800">
                  <div className="text-xs uppercase text-slate-600 font-semibold mb-1">Incr. Cost</div>
                  <div className="text-lg font-mono text-slate-400">${shadowPlan.incremental_cost.toFixed(2)}</div>
                </div>
              </div>

              <div className="mt-6 pt-6 border-t border-slate-800/50 flex justify-between items-center opacity-80">
                <div className="text-xs text-slate-600 font-mono">{shadowPlan.plan_id}</div>
                <div className="text-sm text-slate-500 italic">Held in reserve</div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-800/30 border border-slate-800 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-slate-500">
              <AlertTriangle className="w-8 h-8 mb-2 opacity-50" />
              <p>No valid shadow plan could be generated.</p>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
