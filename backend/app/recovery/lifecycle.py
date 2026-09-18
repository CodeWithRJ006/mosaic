import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.db import RecoveryPlan, Event, Shipment, Vehicle
from app.models.events import EventType
from app.recovery.constraints import HardConstraintFilter

class PlanLifecycle:
    def __init__(self, db: Session, current_version: int, cascaded_events: list):
        self.db = db
        self.current_version = current_version
        self.cascaded_events = cascaded_events

    def approve_plan(self, plan: RecoveryPlan):
        if plan.state_version != self.current_version:
            raise ValueError(f"Stale plan (plan version {plan.state_version} != current {self.current_version})")
            
        # Re-verify hard constraints
        shipment = self.db.query(Shipment).filter(Shipment.id == plan.incident_id).first()
        vehicle_id = plan.vehicles[0] if plan.vehicles else None
        vehicle = self.db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        
        # Pull mock constraint checks from plan for re-evaluation
        pickup_time = datetime.fromisoformat(plan.constraint_checks.get("pickup_time"))
        dropoff_time = datetime.fromisoformat(plan.constraint_checks.get("dropoff_time"))
        
        feasible, reason = HardConstraintFilter.evaluate(
            shipment=shipment,
            vehicle=vehicle,
            pickup_hub=plan.constraint_checks.get("pickup_hub"),
            dropoff_hub=plan.constraint_checks.get("dropoff_hub"),
            pickup_time=pickup_time,
            dropoff_time=dropoff_time,
            current_time=datetime.now(timezone.utc),
            path_min_capacity_weight=plan.constraint_checks.get("path_min_weight", 0),
            path_min_capacity_volume=plan.constraint_checks.get("path_min_volume", 0)
        )
        
        if not feasible:
            raise ValueError(f"Hard constraints failed during approval: {reason.value}")
            
        plan.status = "APPROVED"
        self.cascaded_events.append((
            EventType.PLAN_APPROVED,
            {"plan_id": plan.plan_id, "incident_id": plan.incident_id}
        ))

    def check_staleness(self, event: Event):
        # 1. Find all APPROVED plans
        approved_plans = self.db.query(RecoveryPlan).filter(RecoveryPlan.status == "APPROVED").all()
        
        for plan in approved_plans:
            # Does this event affect the plan's entities?
            # Basic matching: if event payload mentions incident_id or vehicle
            payload_values = list(event.payload.values())
            
            affected = False
            if plan.incident_id in payload_values:
                affected = True
            for v in plan.vehicles:
                if v in payload_values:
                    affected = True
                    
            if affected:
                # Invalidate
                plan.status = "INVALIDATED"
                self.cascaded_events.append((
                    EventType.PLAN_INVALIDATED,
                    {"plan_id": plan.plan_id, "reason": f"State mutated by event {event.id}"}
                ))
                
                # Check for a SHADOW plan to promote
                shadow_plan = self.db.query(RecoveryPlan).filter(
                    RecoveryPlan.incident_id == plan.incident_id,
                    RecoveryPlan.strategy == "SHADOW",
                    RecoveryPlan.status.in_(["DRAFT", "FEASIBLE"]) # Shadow hasn't been approved yet
                ).first()
                
                if shadow_plan:
                    try:
                        # Bump version to current state version so it can be approved
                        shadow_plan.state_version = self.current_version
                        self.approve_plan(shadow_plan)
                        # The approve_plan method will append PLAN_APPROVED for the shadow.
                        # This effectively 'promotes' it.
                    except ValueError:
                        # Shadow is also invalid, requires replanning (which would be handled asynchronously or by a consumer)
                        shadow_plan.status = "INVALIDATED"
                        self.cascaded_events.append((
                            EventType.PLAN_INVALIDATED,
                            {"plan_id": shadow_plan.plan_id, "reason": "Shadow failed promotion"}
                        ))
