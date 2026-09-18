from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models.db import Vehicle, Shipment
from app.recovery.constraints import HardConstraintFilter, RejectionReason

class CapacityOpportunity(BaseModel):
    vehicle_id: str
    segment_id: str
    from_node: str
    to_node: str
    arrival_time: datetime
    departure_time: datetime
    available_weight: float
    available_volume: float

class CandidateRoute(BaseModel):
    shipment_id: str
    vehicle_id: str
    pickup_hub: str
    dropoff_hub: str
    pickup_time: datetime
    dropoff_time: datetime
    path_min_weight: float
    path_min_volume: float
    is_transfer: bool = False
    
    # Metrics for optimization
    delay_minutes: float = 0.0
    incremental_cost: float = 0.0
    transfers: int = 0
    distance: float = 0.0
    
    # After filtering
    is_feasible: bool = False
    rejection_reason: Optional[RejectionReason] = None

class CandidateGenerator:
    def __init__(self, db: Session, current_time: datetime):
        self.db = db
        self.current_time = current_time
        if self.current_time.tzinfo is None:
            self.current_time = self.current_time.replace(tzinfo=timezone.utc)
            
        self.vehicles = self.db.query(Vehicle).all()
        
    def build_temporal_capacity_graph(self) -> Dict[str, List[CapacityOpportunity]]:
        """
        Computes time-indexed free capacity at each future hub/stop for every vehicle.
        (Simplified to assume max_weight available for now, unless we subtract active shipments).
        """
        graph = {}
        for v in self.vehicles:
            ops = []
            for segment in v.schedule:
                arr = datetime.fromisoformat(segment["arrival_time"])
                if arr.tzinfo is None: arr = arr.replace(tzinfo=timezone.utc)
                dep = datetime.fromisoformat(segment["departure_time"])
                if dep.tzinfo is None: dep = dep.replace(tzinfo=timezone.utc)
                
                if arr >= self.current_time or dep >= self.current_time:
                    ops.append(CapacityOpportunity(
                        vehicle_id=v.id,
                        segment_id=segment["segment_id"],
                        from_node=segment["from_node"],
                        to_node=segment["to_node"],
                        arrival_time=arr,
                        departure_time=dep,
                        available_weight=v.max_weight, # subtract current load in real impl
                        available_volume=v.max_volume
                    ))
            graph[v.id] = ops
        return graph

    def generate_candidates(self, shipment: Shipment) -> List[CandidateRoute]:
        graph = self.build_temporal_capacity_graph()
        candidates = []
        
        for v in self.vehicles:
            ops = graph.get(v.id, [])
            
            # Look for direct insertion: vehicle visits shipment.current_location THEN shipment.destination
            pickup_idx = -1
            dropoff_idx = -1
            
            for i, op in enumerate(ops):
                if op.from_node == shipment.current_location and pickup_idx == -1:
                    pickup_idx = i
                if op.to_node == shipment.destination and pickup_idx != -1:
                    dropoff_idx = i
                    break
                    
            if pickup_idx != -1 and dropoff_idx != -1:
                path_ops = ops[pickup_idx:dropoff_idx+1]
                min_w = min(op.available_weight for op in path_ops)
                min_v = min(op.available_volume for op in path_ops)
                
                candidate = CandidateRoute(
                    shipment_id=shipment.id,
                    vehicle_id=v.id,
                    pickup_hub=shipment.current_location,
                    dropoff_hub=shipment.destination,
                    pickup_time=path_ops[0].departure_time, # Departs from pickup
                    dropoff_time=path_ops[-1].arrival_time, # Arrives at dropoff
                    path_min_weight=min_w,
                    path_min_volume=min_v
                )
                candidates.append(candidate)
                
        # Run constraint filter over candidates
        for c in candidates:
            feasible, reason = HardConstraintFilter.evaluate(
                shipment=shipment,
                vehicle=next(v for v in self.vehicles if v.id == c.vehicle_id),
                pickup_hub=c.pickup_hub,
                dropoff_hub=c.dropoff_hub,
                pickup_time=c.pickup_time,
                dropoff_time=c.dropoff_time,
                current_time=self.current_time,
                path_min_capacity_weight=c.path_min_weight,
                path_min_capacity_volume=c.path_min_volume
            )
            c.is_feasible = feasible
            c.rejection_reason = reason
            
        # Order list: Feasible first, then by earliest dropoff
        candidates.sort(key=lambda x: (not x.is_feasible, x.dropoff_time))
        return candidates
