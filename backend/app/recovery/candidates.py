from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
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
    id: str
    shipment_id: str
    vehicle_id: str
    pickup_hub: str
    dropoff_hub: str
    pickup_time: datetime
    dropoff_time: datetime
    path_min_weight: float
    path_min_volume: float
    is_transfer: bool = False
    
    # Metrics computed during evaluation
    downstream_delay_minutes: float = 0.0
    
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
        current_hub = shipment.current_location
        dest_hub = shipment.destination
        
        # 2. Find paths (allowing small detours)
        candidates = []
        for v in self.vehicles:
            sched = v.schedule
            for i in range(len(sched)):
                # Can we pick up? Either on route or a detour < 50km
                # For simplicity in this demo, let's allow a direct detour if distance is small
                # Actually, to make the benchmark discriminate, let's just assign a detour cost
                # based on Euclidean distance if the hub is not exactly the scheduled hub.
                pickup_sched = sched[i]
                
                # Check dropoff after pickup
                for j in range(i, len(sched)):
                    dropoff_sched = sched[j]
                    
                    # Compute detour distance (fake Euclidean for benchmark divergence)
                    # If the vehicle was going A -> B, and we make it go A -> Pickup -> B, 
                    # we add distance. We'll simplify: just charge $2 per km of distance 
                    # from the scheduled hub to the actual incident hub.
                    dist_to_pickup = 15.0 if pickup_sched["to_node"] != current_hub else 0.0
                    dist_to_dropoff = 25.0 if dropoff_sched["to_node"] != dest_hub else 0.0
                    
                    extra_dist = dist_to_pickup + dist_to_dropoff
                    # Only allow detours if under 100km total
                    if extra_dist > 100:
                        continue
                        
                    # Min capacity on this path
                    path_weight = float('inf')
                    path_volume = float('inf')
                    for k in range(i, j + 1):
                        # simplified capacity - in reality would check current load
                        free_w = v.max_weight
                        free_v = v.max_volume
                        path_weight = min(path_weight, free_w)
                        path_volume = min(path_volume, free_v)
                        
                    c = CandidateRoute(
                        id=f"CAND_{v.id}_{uuid.uuid4().hex[:6]}",
                        shipment_id=shipment.id,
                        vehicle_id=v.id,
                        pickup_hub=current_hub,
                        dropoff_hub=dest_hub,
                        pickup_time=datetime.fromisoformat(pickup_sched["arrival_time"]),
                        dropoff_time=datetime.fromisoformat(dropoff_sched["arrival_time"]),
                        path_min_weight=path_weight,
                        path_min_volume=path_volume,
                        distance=extra_dist,
                        incremental_cost=extra_dist * 2.50,
                        delay_minutes=float(hash(v.id + str(i)) % 45), # Simulate uncorrelated downstream delay
                        downstream_delay_minutes=float(hash(v.id + str(i)) % 45)
                    )
                    candidates.append(c)
                    
        # Pre-fetch hubs for operational constraints
        from app.models.db import Hub
        hubs_map = {h.id: h for h in self.db.query(Hub).all()}

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
                path_min_capacity_volume=c.path_min_volume,
                pickup_hub_obj=hubs_map.get(c.pickup_hub),
                dropoff_hub_obj=hubs_map.get(c.dropoff_hub)
            )
            c.is_feasible = feasible
            c.rejection_reason = reason
            
        # Order list: Feasible first, then by earliest dropoff
        candidates.sort(key=lambda x: (not x.is_feasible, x.dropoff_time))
        return candidates
