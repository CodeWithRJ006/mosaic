import collections
import time
from ortools.sat.python import cp_model
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel
import logging
from app.recovery.candidates import CandidateRoute
from app.models.db import Shipment

class OptimizeResult(BaseModel):
    status: str
    primary: Optional[List[CandidateRoute]] = None
    shadow: Optional[List[CandidateRoute]] = None
    rejection_breakdown: Dict[str, int] = {}

class ORToolsOptimizer:
    def __init__(self, shipments: List[Shipment], all_candidates: List[CandidateRoute], time_limit_seconds: float = 2.0):
        self.shipments = shipments
        self.all_candidates = all_candidates
        self.time_limit = time_limit_seconds
        self.logger = logging.getLogger("Optimizer")
        
    def solve(self) -> OptimizeResult:
        feasible = [c for c in self.all_candidates if c.is_feasible]
        rejected = [c for c in self.all_candidates if not c.is_feasible]
        
        breakdown = collections.Counter([c.rejection_reason.value for c in rejected if c.rejection_reason])
        
        if not feasible:
            return OptimizeResult(status="NO_FEASIBLE_PIGGYBACK", rejection_breakdown=dict(breakdown))
            
        primary, status = self._lexicographic_solve(feasible)
        
        if not primary:
            return OptimizeResult(status="NO_FEASIBLE_PIGGYBACK", rejection_breakdown=dict(breakdown))
            
        # Shadow: strictly independent (excluding primary's vehicles)
        primary_vehicles = {c.vehicle_id for c in primary}
        shadow_candidates = [c for c in feasible if c.vehicle_id not in primary_vehicles]
        
        shadow, _ = self._lexicographic_solve(shadow_candidates) if shadow_candidates else (None, "NO_FEASIBLE_PIGGYBACK")
            
        return OptimizeResult(status=status, primary=primary, shadow=shadow, rejection_breakdown=dict(breakdown))
        
    def _lexicographic_solve(self, candidates: List[CandidateRoute]) -> Tuple[Optional[List[CandidateRoute]], str]:
        start_time = time.time()
        
        model = cp_model.CpModel()
        
        # Variables: x[i] is True if candidates[i] is selected
        x = [model.NewBoolVar(f"x_{i}") for i in range(len(candidates))]
        
        # Scale float values to integers for CP-SAT (up to 3 decimal places)
        SCALE = 1000
        
        # Shipments mapping
        shipment_to_cands = collections.defaultdict(list)
        for i, c in enumerate(candidates):
            shipment_to_cands[c.shipment_id].append(i)
            
        # Constraint: At most one candidate per shipment
        for s_id, c_indices in shipment_to_cands.items():
            model.AddAtMostOne([x[i] for i in c_indices])
            
        # Constraint: Capacity
        vehicle_to_cands = collections.defaultdict(list)
        for i, c in enumerate(candidates):
            vehicle_to_cands[c.vehicle_id].append((i, c))
            
        s_map = {s.id: s.weight for s in self.shipments}
        for v_id, c_data in vehicle_to_cands.items():
            cap_limit = int(max([c.path_min_weight for _, c in c_data]) * SCALE)
            model.Add(sum(int(s_map[c.shipment_id] * SCALE) * x[i] for i, c in c_data) <= cap_limit)

        solver = cp_model.CpSolver()
        
        # Objectives in order
        def get_time_left():
            return max(0.1, self.time_limit - (time.time() - start_time))

        def solve_stage(objective_expr, maximize: bool):
            if maximize:
                model.Maximize(objective_expr)
            else:
                model.Minimize(objective_expr)
            solver.parameters.max_time_in_seconds = get_time_left()
            return solver.Solve(model)

        # Stage 1: Maximize SLA feasibility (count of recovered shipments)
        sla_expr = sum(x)
        status = solve_stage(sla_expr, True)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None, "NO_FEASIBLE_PIGGYBACK"
            
        max_recovered = int(solver.ObjectiveValue())
        model.Add(sla_expr == max_recovered)
        
        # Stage 2: Minimize delay
        delay_expr = sum(int(candidates[i].delay_minutes * SCALE) * x[i] for i in range(len(x)))
        status = solve_stage(delay_expr, False)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            min_delay = int(solver.ObjectiveValue())
            model.Add(delay_expr == min_delay)
            
        # Stage 3: Minimize cost
        cost_expr = sum(int(candidates[i].incremental_cost * SCALE) * x[i] for i in range(len(x)))
        status = solve_stage(cost_expr, False)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            min_cost = int(solver.ObjectiveValue())
            model.Add(cost_expr == min_cost)
            
        # Stage 4: Minimize transfers
        transfers_expr = sum(int(candidates[i].transfers) * x[i] for i in range(len(x)))
        status = solve_stage(transfers_expr, False)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            min_transfers = int(solver.ObjectiveValue())
            model.Add(transfers_expr == min_transfers)
            
        # Stage 5: Minimize distance
        dist_expr = sum(int(candidates[i].distance * SCALE) * x[i] for i in range(len(x)))
        status = solve_stage(dist_expr, False)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            min_dist = int(solver.ObjectiveValue())
            model.Add(dist_expr == min_dist)
            
        # Extract selected candidates
        selected = []
        for i in range(len(candidates)):
            if solver.BooleanValue(x[i]):
                selected.append(candidates[i])
                
        final_status = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
        self.logger.info(f"CP-SAT Lexicographic Solve complete. Status: {final_status}. Time left: {get_time_left()}s")
        return selected, final_status
