import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from app.db import SessionLocal
from app.models.db import Shipment, Vehicle, Event, RecoveryPlan
from app.models.events import EventType
from app.state.manager import StateManager
from app.recovery.lifecycle import PlanLifecycle

@pytest.fixture(autouse=True)
def setup_db():
    db = SessionLocal()
    db.query(Event).delete()
    db.query(RecoveryPlan).delete()
    db.query(Vehicle).delete()
    db.query(Shipment).delete()
    
    now = datetime.now(timezone.utc)
    
    s1 = Shipment(id="S1", weight=10.0, volume=1.0, origin="H1", destination="H2", sla_deadline=now + timedelta(hours=5), current_location="H1", planned_route=[], status="PLANNED")
    v1 = Vehicle(id="V1", max_weight=100.0, max_volume=10.0, current_location="H1", schedule=[], shift_start=now, shift_end=now+timedelta(hours=5))
    v2 = Vehicle(id="V2", max_weight=100.0, max_volume=10.0, current_location="H1", schedule=[], shift_start=now, shift_end=now+timedelta(hours=5))
    
    db.add(s1)
    db.add(v1)
    db.add(v2)
    db.commit()
    db.close()
    
    yield
    
    db = SessionLocal()
    db.query(Event).delete()
    db.query(RecoveryPlan).delete()
    db.query(Vehicle).delete()
    db.query(Shipment).delete()
    db.commit()
    db.close()

def test_plan_lifecycle_and_staleness():
    db = SessionLocal()
    manager = StateManager(db)
    
    now = datetime.now(timezone.utc)
    
    # 1. Create a DRAFT primary plan on V1
    primary_plan = RecoveryPlan(
        plan_id="P_PRIMARY",
        incident_id="S1",
        state_version=manager.current_version,
        incident_version=1,
        strategy="PRIMARY",
        status="DRAFT",
        vehicles=["V1"],
        transfers=[],
        eta=now + timedelta(hours=2),
        incremental_cost=10.0,
        extra_distance=5.0,
        sla_margin_minutes=60.0,
        constraint_checks={
            "pickup_hub": "H1", "dropoff_hub": "H2",
            "pickup_time": (now + timedelta(minutes=5)).isoformat(), "dropoff_time": (now + timedelta(hours=2)).isoformat(),
            "path_min_weight": 100.0, "path_min_volume": 10.0
        },
        rejection_reasons={},
        created_at=now
    )
    
    # 2. Create a DRAFT shadow plan on V2
    shadow_plan = RecoveryPlan(
        plan_id="P_SHADOW",
        incident_id="S1",
        state_version=manager.current_version,
        incident_version=1,
        strategy="SHADOW",
        status="DRAFT",
        vehicles=["V2"],
        transfers=[],
        eta=now + timedelta(hours=2.5),
        incremental_cost=15.0,
        extra_distance=10.0,
        sla_margin_minutes=30.0,
        constraint_checks={
            "pickup_hub": "H1", "dropoff_hub": "H2",
            "pickup_time": (now + timedelta(minutes=5)).isoformat(), "dropoff_time": (now + timedelta(hours=2.5)).isoformat(),
            "path_min_weight": 100.0, "path_min_volume": 10.0
        },
        rejection_reasons={},
        created_at=now
    )
    
    db.add(primary_plan)
    db.add(shadow_plan)
    db.commit()
    
    # 3. Approve primary
    lifecycle = PlanLifecycle(db, manager.current_version, [])
    lifecycle.approve_plan(primary_plan)
    db.commit()
    assert primary_plan.status == "APPROVED"
    assert shadow_plan.status == "DRAFT"
    
    # 4. Mutate V1 (triggering invalidation)
    # Using the StateManager dispatch so the lifecycle cascade runs
    asyncio.run(manager.dispatch(
        EventType.VEHICLE_POSITION_UPDATED,
        {"vehicle_id": "V1", "location": "H_BREAK", "timestamp": now.isoformat()}
    ))
    
    # 5. Refresh from DB and verify cascading effects
    db.refresh(primary_plan)
    db.refresh(shadow_plan)
    
    # Primary should be INVALIDATED because V1 mutated
    assert primary_plan.status == "INVALIDATED"
    
    # Shadow should be APPROVED because it was promoted
    assert shadow_plan.status == "APPROVED"
    
    db.close()
