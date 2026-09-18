import pytest
import json
import asyncio
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.state.manager import StateManager
from app.models.events import EventType
from app.db import SessionLocal
from app.models.db import Event, Vehicle

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    db.query(Event).delete()
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(Event).delete()
    db.commit()
    db.close()

def test_state_engine_and_ws():
    with client.websocket_connect("/ws/state") as websocket:
        db = SessionLocal()
        manager = StateManager(db)
        
        initial_version = manager.current_version
        assert initial_version == 0
        
        # 1. Accept valid event
        valid_payload = {
            "vehicle_id": "V1",
            "location": "H2",
            "timestamp": "2026-09-18T10:00:00Z"
        }
        
        # We need an event loop to run async dispatch in sync test context
        event = asyncio.run(manager.dispatch(EventType.VEHICLE_POSITION_UPDATED, valid_payload))
        
        # State version should increment
        assert manager.current_version == 1
        assert event.state_version == 1
        
        # WS should receive it
        ws_msg = websocket.receive_text()
        ws_data = json.loads(ws_msg)
        assert ws_data["type"] == "STATE_UPDATED"
        assert ws_data["state_version"] == 1
        assert ws_data["payload"]["event_type"] == EventType.VEHICLE_POSITION_UPDATED.value
        
        # 2. Reject malformed event
        invalid_payload = {
            "vehicle_id": "V1" # missing location & timestamp
        }
        
        with pytest.raises(ValueError):
            asyncio.run(manager.dispatch(EventType.VEHICLE_POSITION_UPDATED, invalid_payload))
            
        assert manager.current_version == 1 # Did not increment
        
        # 3. Test replay
        events_in_db = db.query(Event).order_by(Event.state_version.asc()).all()
        assert len(events_in_db) == 1
        
        # Create a fresh manager simulating a t=0 replay
        replay_manager = StateManager(db)
        # It picks up the current max version from DB
        assert replay_manager.current_version == 1
        
        # Explicit replay test
        db.query(Vehicle).delete()
        v = Vehicle(id="V1", max_weight=100.0, max_volume=10.0, current_location="H1", schedule=[], shift_start=datetime.now(timezone.utc), shift_end=datetime.now(timezone.utc))
        db.add(v)
        db.commit()
        
        replay_manager._apply_projection(events_in_db[0])
        db.commit()
        
        v_updated = db.query(Vehicle).filter_by(id="V1").first()
        assert v_updated.current_location == "H2" # Same as the event payload
        
        db.close()
