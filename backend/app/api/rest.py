from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.db import get_db
from app.models.db import Shipment, Vehicle, Hub, Event, RecoveryPlan
from app.models.events import EventType
from app.state.manager import StateManager
from app.recovery.candidates import CandidateGenerator, CandidateRoute
from app.recovery.constraints import HardConstraintFilter
from app.recovery.optimizer import ORToolsOptimizer
from app.recovery.receipt import ReceiptBuilder, DecisionReceipt
from app.recovery.lifecycle import PlanLifecycle

router = APIRouter()

@router.get("/state")
def get_state(db: Session = Depends(get_db)):
    manager = StateManager(db)
    return {
        "state_version": manager.current_version,
        "shipments": [s.id for s in db.query(Shipment).all()],
        "vehicles": [v.id for v in db.query(Vehicle).all()],
        "hubs": [h.id for h in db.query(Hub).all()]
    }

class GenericEventReq(Dict[str, Any]):
    pass

@router.post("/events/{event_type}")
async def submit_event(event_type: str, payload: dict, db: Session = Depends(get_db)):
    manager = StateManager(db)
    try:
        # Map kebab-case from URL to enum if needed, or assume literal
        et = event_type.replace("-", "_").upper()
        await manager.dispatch(et, payload)
        return {"status": "ok", "state_version": manager.current_version}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/disruptions/inject")
async def inject_disruption(payload: dict, db: Session = Depends(get_db)):
    """
    payload: {"disruption_type": "delay_vehicle", "payload": {"vehicle_id": "V1", ...}}
    """
    manager = StateManager(db)
    d_type = payload.get("disruption_type")
    inner_payload = payload.get("payload", {})
    
    # Map high-level UI disruptions to core events
    d_map = {
        "delay_vehicle": EventType.VEHICLE_DELAYED.value,
        "close_hub": EventType.HUB_CLOSED.value,
        "reduce_capacity": EventType.CAPACITY_CHANGED.value,
        "misroute_shipment": EventType.SHIPMENT_MISROUTED.value
    }
    
    event_type = d_map.get(d_type, d_type)
    
    # inject timestamp if not present
    if "timestamp" not in inner_payload:
        inner_payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        
    try:
        await manager.dispatch(event_type, inner_payload)
        return {"status": "injected", "event_type": event_type, "state_version": manager.current_version}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/recovery/generate", response_model=DecisionReceipt)
def generate_recovery(payload: dict, db: Session = Depends(get_db)):
    shipment_id = payload.get("shipment_id")
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
        
    now = datetime.now(timezone.utc)
    
    # 1. Candidate Generation
    gen = CandidateGenerator(db, current_time=now)
    candidates = gen.generate_candidates(shipment)
    
    # 2. Hard Constraint Filter
    for c in candidates:
        v = db.query(Vehicle).filter(Vehicle.id == c.vehicle_id).first()
        feasible, reason = HardConstraintFilter.evaluate(
            shipment=shipment,
            vehicle=v,
            pickup_hub=c.pickup_hub,
            dropoff_hub=c.dropoff_hub,
            pickup_time=c.pickup_time,
            dropoff_time=c.dropoff_time,
            current_time=now,
            path_min_capacity_weight=c.path_min_weight,
            path_min_capacity_volume=c.path_min_volume
        )
        c.is_feasible = feasible
        c.rejection_reason = reason
        
    # 3. Optimize
    opt = ORToolsOptimizer(shipments=[shipment], all_candidates=candidates)
    result = opt.solve()
    
    # 4. Save to DB
    manager = StateManager(db)
    primary_c = result.primary[0] if result.primary else None
    shadow_c = result.shadow[0] if result.shadow else None
    
    def _create_db_plan(c: CandidateRoute, strategy: str, status: str) -> RecoveryPlan:
        return RecoveryPlan(
            plan_id=f"PLAN_{uuid.uuid4().hex[:8].upper()}",
            incident_id=shipment.id,
            state_version=manager.current_version,
            incident_version=manager.current_version,
            strategy=strategy,
            status=status,
            vehicles=[c.vehicle_id],
            transfers=[],
            eta=c.dropoff_time,
            incremental_cost=c.incremental_cost,
            extra_distance=c.distance,
            sla_margin_minutes=0.0, # Handled in receipt check
            constraint_checks={
                "pickup_hub": c.pickup_hub, "dropoff_hub": c.dropoff_hub,
                "pickup_time": c.pickup_time.isoformat(), "dropoff_time": c.dropoff_time.isoformat(),
                "path_min_weight": c.path_min_weight, "path_min_volume": c.path_min_volume
            },
            rejection_reasons={},
            created_at=now
        )
        
    primary_plan = None
    if primary_c:
        primary_plan = _create_db_plan(primary_c, "PRIMARY", "FEASIBLE")
        db.add(primary_plan)
    
    shadow_plan = None
    if shadow_c:
        shadow_plan = _create_db_plan(shadow_c, "SHADOW", "FEASIBLE")
        db.add(shadow_plan)
        
    db.commit()
    
    # 5. Build Receipt
    receipt = ReceiptBuilder.build_receipt(
        shipment=shipment,
        status=result.status,
        all_candidates=candidates,
        selected_candidate=primary_c,
        current_time=now
    )
    
    # Embellish receipt with plan_id (for the API to use for approval)
    receipt_dict = receipt.model_dump()
    if primary_plan:
        receipt_dict["plan_id"] = primary_plan.plan_id
        
    return receipt_dict

@router.post("/recovery/{plan_id}/approve")
def approve_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(RecoveryPlan).filter(RecoveryPlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    manager = StateManager(db)
    lifecycle = PlanLifecycle(db, manager.current_version, [])
    
    try:
        lifecycle.approve_plan(plan)
        db.commit()
        return {"status": "APPROVED", "plan_id": plan.plan_id}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("/recovery/{shipment_id}/active")
def get_active_plan(shipment_id: str, db: Session = Depends(get_db)):
    plan = db.query(RecoveryPlan).filter(
        RecoveryPlan.incident_id == shipment_id,
        RecoveryPlan.status == "APPROVED"
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="No active approved plan")
    return {"plan_id": plan.plan_id, "strategy": plan.strategy, "status": plan.status}
