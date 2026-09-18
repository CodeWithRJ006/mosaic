import pytest
from datetime import datetime, timezone, timedelta
from app.db import SessionLocal
from app.models.db import Shipment, Vehicle, Hub
from app.recovery.candidates import CandidateGenerator
from app.simulator.scenario import ScenarioGenerator

@pytest.fixture(autouse=True)
def setup_seeded_world():
    db = SessionLocal()
    # Clear tables
    db.query(Shipment).delete()
    db.query(Vehicle).delete()
    db.query(Hub).delete()
    
    # Generate seed 58291
    gen = ScenarioGenerator(58291)
    hubs, vehicles, shipments = gen.generate()
    
    db.add_all(hubs)
    db.add_all(vehicles)
    db.add_all(shipments)
    db.commit()
    
    yield
    
    db = SessionLocal()
    db.query(Shipment).delete()
    db.query(Vehicle).delete()
    db.query(Hub).delete()
    db.commit()
    db.close()

def test_integration_candidate_generation():
    db = SessionLocal()
    
    # Let's pick a shipment to disrupt
    s = db.query(Shipment).first()
    assert s is not None
    
    # We set current time to just after generator's base time
    gen = ScenarioGenerator(58291)
    current_time = gen.base_time + timedelta(minutes=10)
    
    generator = CandidateGenerator(db, current_time)
    
    # Force some candidates to fail SLA deadline by artificially tightening it
    s.sla_deadline = current_time + timedelta(hours=1)
    
    candidates = generator.generate_candidates(s)
    
    N = len(candidates)
    assert N > 0, "Expected at least one candidate path from the temporal graph"
    
    feasible_candidates = [c for c in candidates if c.is_feasible]
    rejected_candidates = [c for c in candidates if not c.is_feasible]
    
    M = len(feasible_candidates)
    
    assert M < N, "Expected at least some candidates to be rejected"
    
    for rc in rejected_candidates:
        assert rc.rejection_reason is not None, "Rejected candidates must have a reason"
        
    db.close()
