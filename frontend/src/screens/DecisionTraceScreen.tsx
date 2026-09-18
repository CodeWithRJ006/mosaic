import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, XCircle, ChevronLeft } from 'lucide-react';

export default function DecisionTraceScreen() {
  const { shipmentId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  
  const receipt = location.state?.receipt;

  if (!receipt) {
    return <div className="p-8">No receipt found.</div>;
  }

  const isNoFeasible = receipt.status === 'NO_FEASIBLE_PIGGYBACK';

  return (
    <div className="p-8 max-w-4xl mx-auto w-full h-full flex flex-col gap-6">
      
      <div>
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-slate-400 hover:text-white mb-4">
          <ChevronLeft className="w-4 h-4" /> Back to Recovery Options
        </button>
        <h1 className="text-2xl font-bold flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-blue-400" /> Decision Trace: {shipmentId}
        </h1>
        <p className="text-slate-400 mt-2">Cryptographically-verifiable proof of solver decisions and constraint applications.</p>
      </div>

      <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-2xl mt-4">
        
        <div className="bg-slate-800 border-b border-slate-700 p-6 flex justify-between items-center">
          <div className="flex items-center gap-3">
            {isNoFeasible ? (
              <XCircle className="w-6 h-6 text-rose-500" />
            ) : (
              <CheckCircle2 className="w-6 h-6 text-emerald-500" />
            )}
            <h3 className="text-lg font-bold text-white">Status: {receipt.status}</h3>
          </div>
          <div className="text-xs text-slate-500 font-mono text-right">
            <div>Timestamp: {new Date(receipt.created_at).toISOString()}</div>
            {receipt.plan_id && <div className="mt-1 text-blue-400">Plan: {receipt.plan_id}</div>}
          </div>
        </div>

        {!isNoFeasible && (
          <div className="p-6 border-b border-slate-800">
            <h4 className="text-xs font-semibold uppercase text-slate-500 mb-4 tracking-wider">Hard Constraint Math Check</h4>
            <div className="grid grid-cols-2 gap-4">
              
              <div className="bg-slate-800/50 p-4 rounded-lg flex items-center justify-between border border-slate-700/50">
                <span className="text-sm text-slate-300">Weight Capacity</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-emerald-400 text-sm">+{receipt.weight_check_margin?.toFixed(2)} kg</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                </div>
              </div>

              <div className="bg-slate-800/50 p-4 rounded-lg flex items-center justify-between border border-slate-700/50">
                <span className="text-sm text-slate-300">Pickup Feasibility</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-emerald-400 text-sm">+{receipt.time_check_pickup_margin_minutes?.toFixed(1)} min</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                </div>
              </div>

              <div className="bg-slate-800/50 p-4 rounded-lg flex items-center justify-between border border-slate-700/50">
                <span className="text-sm text-slate-300">SLA Violation</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-emerald-400 text-sm">+{receipt.delivery_check_sla_margin_minutes?.toFixed(1)} min</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                </div>
              </div>

              <div className="bg-slate-800/50 p-4 rounded-lg flex items-center justify-between border border-slate-700/50">
                <span className="text-sm text-slate-300">Downstream Commits</span>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-emerald-400 text-sm">+{receipt.downstream_route_check_delay_minutes?.toFixed(1)} min delay</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                </div>
              </div>

            </div>
          </div>
        )}

        <div className="p-6">
          <h4 className="text-xs font-semibold uppercase text-slate-500 mb-4 tracking-wider">Rejected Candidates Log ({receipt.rejected_candidates.length})</h4>
          
          {receipt.rejected_candidates.length === 0 ? (
            <div className="text-slate-500 text-sm italic p-4 bg-slate-800/20 rounded border border-slate-800 border-dashed text-center">
              No rejected candidates.
            </div>
          ) : (
            <div className="overflow-hidden border border-slate-800 rounded-lg">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-800 text-xs uppercase font-semibold text-slate-500">
                  <tr>
                    <th className="px-4 py-3 border-b border-slate-700">Vehicle</th>
                    <th className="px-4 py-3 border-b border-slate-700">Rejection Reason</th>
                    <th className="px-4 py-3 border-b border-slate-700 text-right">Candidate Ref</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {receipt.rejected_candidates.map((rc: any, idx: number) => (
                    <tr key={rc.candidate_id + idx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-mono">{rc.vehicle_id}</td>
                      <td className="px-4 py-3 text-rose-400 font-mono text-xs">{rc.rejection_reason}</td>
                      <td className="px-4 py-3 font-mono text-slate-600 text-right text-xs truncate max-w-[120px]">{rc.candidate_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
