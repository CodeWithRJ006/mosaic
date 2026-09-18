import pytest
import time
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from app.main import app
from app.db import SessionLocal
from app.models.db import Shipment, Vehicle, Event, RecoveryPlan

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown_db():
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
    
    disrupt_res = client.post("/api/disruptions/inject", json={
        "disruption_type": "delay_vehicle",
        "payload": {
            "vehicle_id": selected_vehicle,
            "delay_minutes": 120,
            "timestamp": now.isoformat()
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
