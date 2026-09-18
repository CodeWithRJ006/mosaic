import pytest
import time
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from app.main import app
from app.db import SessionLocal, engine
from app.models.db import Base, Shipment, Vehicle, Event, RecoveryPlan

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    db.query(Event).delete()
    db.query(RecoveryPlan).delete()
    db.query(Vehicle).delete()
    db.query(Shipment).delete()
    
    now = datetime.now(timezone.utc)
    
    s1 = Shipment(id="S1", weight=10.0, volume=1.0, origin="H1", destination="H2", sla_deadline=now + timedelta(hours=5), current_location="H3", planned_route=[], status="PLANNED")
    
    schedule_v1 = [
        {"segment_id": "seg1", "from_node": "H3", "to_node": "H2", "arrival_time": (now + timedelta(hours=1)).isoformat(), "departure_time": (now + timedelta(minutes=5)).isoformat(), "distance": 10}
    ]
    schedule_v2 = [
        {"segment_id": "seg2", "from_node": "H3", "to_node": "H2", "arrival_time": (now + timedelta(hours=1.5)).isoformat(), "departure_time": (now + timedelta(minutes=10)).isoformat(), "distance": 15}
    ]
    
    v1 = Vehicle(id="V1", max_weight=100.0, max_volume=10.0, current_location="H3", schedule=schedule_v1, shift_start=now, shift_end=now+timedelta(hours=5))
    v2 = Vehicle(id="V2", max_weight=100.0, max_volume=10.0, current_location="H3", schedule=schedule_v2, shift_start=now, shift_end=now+timedelta(hours=5))
    
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

def test_api_e2e_recovery_lifecycle():
    now = datetime.now(timezone.utc)
    
    # 1. Inject a misroute via REST (Shipment is misrouted to H3)
    # The fixture already sets it at H3 to make things simple, but let's fire the event anyway to test the endpoint.
    inj_res = client.post("/api/disruptions/inject", json={
        "disruption_type": "misroute_shipment",
        "payload": {
            "shipment_id": "S1",
            "location": "H3",
            "timestamp": now.isoformat()
        }
    })
    assert inj_res.status_code == 200
    
    # 2. Call recovery generation via REST
    rec_res = client.post("/api/recovery/generate", json={"shipment_id": "S1"})
    assert rec_res.status_code == 200
    receipt = rec_res.json()
    assert receipt["status"] in ("OPTIMAL", "FEASIBLE")
    
    plan_id = receipt["plan_id"]
    
    # 3. Approve the primary plan
    app_res = client.post(f"/api/recovery/{plan_id}/approve")
    assert app_res.status_code == 200
    
    # Verify active plan is primary
    active_res = client.get("/api/recovery/S1/active")
    assert active_res.json()["plan_id"] == plan_id
    assert active_res.json()["strategy"] == "PRIMARY"
    
    # 4. Inject a disruption that invalidates the primary plan (Delay the vehicle selected by the plan)
    selected_vehicle = receipt["selected_vehicle_id"]
    
    later_now = datetime.now(timezone.utc)
    disrupt_res = client.post("/api/disruptions/inject", json={
        "disruption_type": "delay_vehicle",
        "payload": {
            "vehicle_id": selected_vehicle,
            "delay_minutes": 120,
            "timestamp": later_now.isoformat()
        }
    })
    assert disrupt_res.status_code == 200
    
    # 5. Confirm shadow promotion via the API
    # The cascade should have run automatically
    new_active_res = client.get("/api/recovery/S1/active")
    assert new_active_res.status_code == 200
    new_active = new_active_res.json()
    
    assert new_active["plan_id"] != plan_id # It changed!
    assert new_active["strategy"] == "SHADOW"
    assert new_active["status"] == "APPROVED"

def test_api_no_feasible_piggyback():
    # Insert a shipment that cannot fit anywhere
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    
    s_giant = Shipment(
        id="S_GIANT", weight=50000.0, volume=500.0, 
        origin="H1", destination="H2", 
        sla_deadline=now + timedelta(hours=5), 
        current_location="H3", planned_route=[], status="PLANNED"
    )
    db.add(s_giant)
    db.commit()
    db.close()
    
    # Inject disruption
    inj_res = client.post("/api/disruptions/inject", json={
        "disruption_type": "misroute_shipment",
        "payload": {
            "shipment_id": "S_GIANT",
            "location": "H3",
            "timestamp": now.isoformat()
        }
    })
    assert inj_res.status_code == 200
    
    # Call recovery generation
    rec_res = client.post("/api/recovery/generate", json={"shipment_id": "S_GIANT"})
    assert rec_res.status_code == 200
    receipt = rec_res.json()
    assert receipt["status"] == "NO_FEASIBLE_PIGGYBACK"
    assert "rejected_candidates" in receipt
    assert len(receipt.get("objective_trace", {})) == 0

def test_api_double_approval_and_stale_event():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    s2 = Shipment(id="S2", weight=10.0, volume=1.0, origin="H1", destination="H2", sla_deadline=now + timedelta(hours=5), current_location="H3", planned_route=[], status="PLANNED")
    db.add(s2)
    db.commit()
    db.close()

    # Call recovery generation
    rec_res = client.post("/api/recovery/generate", json={"shipment_id": "S2"})
    assert rec_res.status_code == 200
    receipt = rec_res.json()
    plan_id = receipt["plan_id"]
    
    # 1. Approve primary plan
    app_res = client.post(f"/api/recovery/{plan_id}/approve")
    assert app_res.status_code == 200
    
    # 2. Try to approve AGAIN
    app_res_double = client.post(f"/api/recovery/{plan_id}/approve")
    assert app_res_double.status_code == 409
    assert "PLAN_ALREADY_APPROVED" in app_res_double.json()["detail"]
    
    # 3. Test Stale Event (Time-travel)
    old_time = now - timedelta(hours=2)
    stale_inj = client.post("/api/disruptions/inject", json={
        "disruption_type": "delay_vehicle",
        "payload": {
            "vehicle_id": "V1",
            "delay_minutes": 10,
            "timestamp": old_time.isoformat()
        }
    })
    assert stale_inj.status_code == 400
    assert "EVENT_REJECTED" in stale_inj.json()["detail"]
