from datetime import datetime, timezone
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class Hub(BaseModel):
    id: str
    name: str
    lat: float
    lon: float

class VehicleSegment(BaseModel):
    segment_id: str
    from_node: str
    to_node: str
    arrival_time: datetime
    departure_time: datetime

class Vehicle(BaseModel):
    id: str
    max_weight: float
    max_volume: float
    current_location: str # Could be a hub ID or coordinates if in transit
    schedule: List[VehicleSegment]

class Shipment(BaseModel):
    id: str
    weight: float
    volume: float
    origin: str
    destination: str
    sla_deadline: datetime
    current_location: str # Hub ID or Vehicle ID
    planned_route: List[str] # List of Hub IDs
    status: str # e.g. "PLANNED", "IN_TRANSIT", "MISROUTED", "DELAYED", "DELIVERED"

class CapacityOpportunity(BaseModel):
    vehicle_id: str
    segment_id: str
    from_node: str
    to_node: str
    arrival_time: datetime
    departure_time: datetime
    available_weight: float
    available_volume: float
    route_direction: str

class ConstraintChecks(BaseModel):
    capacity_ok: bool
    time_window_ok: bool
    transfer_sync_ok: bool
    vehicle_schedule_ok: bool
    
    @property
    def is_feasible(self) -> bool:
        return self.capacity_ok and self.time_window_ok and self.transfer_sync_ok and self.vehicle_schedule_ok

class RecoveryPlan(BaseModel):
    plan_id: str
    incident_id: str
    state_version: int
    incident_version: int
    strategy: str # e.g. "DIRECT_INSERTION", "SINGLE_HUB_TRANSFER", "RESCUE"
    status: str # "PROPOSED", "APPROVED", "REJECTED", "INVALIDATED"
    
    vehicles: List[str]
    transfers: List[str] # Hub IDs where transfers occur
    
    eta: datetime
    incremental_cost: float
    extra_distance: float
    sla_margin_minutes: float
    
    constraint_checks: ConstraintChecks
    rejection_reasons: List[str]
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class NetworkState(BaseModel):
    state_version: int = 1
    hubs: Dict[str, Hub] = {}
    vehicles: Dict[str, Vehicle] = {}
    shipments: Dict[str, Shipment] = {}
    active_plans: Dict[str, RecoveryPlan] = {}
