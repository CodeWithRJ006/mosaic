import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from app.db import SessionLocal
from app.models.db import Vehicle, Event
from app.simulator.engine import SimulationEngine

@pytest.fixture(autouse=True)
def setup_db():
    db = SessionLocal()
    db.query(Event).delete()
    db.query(Vehicle).delete()
    
    start = datetime.now(timezone.utc)
    
    # Create a vehicle with a schedule that spans exactly the next few minutes
    v = Vehicle(
        id="V_SIM_1",
        max_weight=100.0,
        max_volume=10.0,
        current_location="H1",
        shift_start=start,
        shift_end=start + timedelta(hours=1),
        schedule=[
            {
                "segment_id": "S1",
                "from_node": "H1",
                "to_node": "H2",
                "arrival_time": (start + timedelta(seconds=10)).isoformat(),
                "departure_time": (start + timedelta(seconds=20)).isoformat()
            }
        ]
    )
    db.add(v)
    db.commit()
    db.close()
    
    yield
    
    db = SessionLocal()
    db.query(Event).delete()
    db.query(Vehicle).delete()
    db.commit()
    db.close()

def test_simulation_tick():
    engine = SimulationEngine(get_db_session_factory=SessionLocal, time_scale=1.0)
    
    # Tick past the arrival time (10 seconds)
    asyncio.run(engine.tick(15.0))
    
    # This should have triggered an event because the vehicle arrived at H2
    db = SessionLocal()
    events = db.query(Event).all()
    
    assert len(events) == 1
    assert events[0].type == "VEHICLE_POSITION_UPDATED"
    assert events[0].payload["vehicle_id"] == "V_SIM_1"
    assert events[0].payload["location"] == "H2"
    
    db.close()
