from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.db import Shipment, Vehicle
from app.recovery.candidates import CandidateGenerator, CandidateRoute

def solve_baseline(db: Session, shipment: Shipment) -> CandidateRoute:
    """
    Baseline: Nearest Feasible Vehicle.
    Generates candidates based purely on connectivity.
    Filters only on naive capacity and absolute deadline (ignores advanced temporal overlap constraints).
    Picks the one with the smallest extra distance.
    """
    now = datetime.now(timezone.utc)
    gen = CandidateGenerator(db, current_time=now)
    candidates = gen.generate_candidates(shipment)
    
    feasible = []
    for c in candidates:
        v = db.query(Vehicle).filter(Vehicle.id == c.vehicle_id).first()
        
        # Naive capacity check
        if c.path_min_weight < shipment.weight or c.path_min_volume < shipment.volume:
            continue
            
        # Naive deadline check
        if c.dropoff_time > shipment.sla_deadline.replace(tzinfo=timezone.utc) if shipment.sla_deadline.tzinfo is None else shipment.sla_deadline:
            continue
            
        feasible.append(c)
        
    if not feasible:
        return None
        
    return min(feasible, key=lambda c: c.distance)
