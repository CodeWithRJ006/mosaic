import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.db import Shipment, Vehicle
from app.recovery.candidates import CandidateGenerator
from app.recovery.constraints import HardConstraintFilter
from app.recovery.optimizer import ORToolsOptimizer
from app.bench.baseline import solve_baseline

def run_recovery_bench(db: Session, shipment_id: str):
    """
    Runs both MOSAIC and Baseline on a single disrupted shipment.
    Returns metrics dictionary.
    """
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    now = datetime.now(timezone.utc)
    
    # --- MOSAIC ---
    start_t = time.perf_counter()
    gen = CandidateGenerator(db, current_time=now)
    candidates = gen.generate_candidates(shipment)
    
    for c in candidates:
        v = db.query(Vehicle).filter(Vehicle.id == c.vehicle_id).first()
        feasible, reason = HardConstraintFilter.evaluate(
            shipment=shipment, vehicle=v, pickup_hub=c.pickup_hub, dropoff_hub=c.dropoff_hub,
            pickup_time=c.pickup_time, dropoff_time=c.dropoff_time, current_time=now,
            path_min_capacity_weight=c.path_min_weight, path_min_capacity_volume=c.path_min_volume
        )
        c.is_feasible = feasible
        c.rejection_reason = reason
        
    opt = ORToolsOptimizer(shipments=[shipment], all_candidates=candidates)
    result = opt.solve()
    mosaic_latency = (time.perf_counter() - start_t) * 1000
    
    mosaic_plan = result.primary[0] if result.primary else None
    
    # --- BASELINE ---
    start_t = time.perf_counter()
    baseline_plan = solve_baseline(db, shipment)
    baseline_latency = (time.perf_counter() - start_t) * 1000
    
    # --- METRICS ---
    def extract_metrics(plan, latency):
        if not plan:
            return {
                "success": False,
                "sla_violation": False,
                "cost": 0.0,
                "distance": 0.0,
                "latency": latency
            }
            
        dt = plan.dropoff_time.replace(tzinfo=timezone.utc) if plan.dropoff_time.tzinfo is None else plan.dropoff_time
        sla = shipment.sla_deadline.replace(tzinfo=timezone.utc) if shipment.sla_deadline.tzinfo is None else shipment.sla_deadline
        
        return {
            "success": True,
            "sla_violation": dt > sla,
            "cost": plan.incremental_cost,
            "distance": plan.distance,
            "latency": latency
        }
        
    return {
        "mosaic": extract_metrics(mosaic_plan, mosaic_latency),
        "baseline": extract_metrics(baseline_plan, baseline_latency)
    }
