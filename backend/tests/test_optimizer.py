import pytest
from datetime import datetime, timezone
from app.recovery.optimizer import ORToolsOptimizer, OptimizeResult
from app.recovery.candidates import CandidateRoute
from app.recovery.constraints import RejectionReason
from app.models.db import Shipment

def test_shared_scarce_capacity():
    now = datetime.now(timezone.utc)
    
    # 3 shipments, total weight 130
    s1 = Shipment(id="S1", weight=50.0, volume=1.0)
    s2 = Shipment(id="S2", weight=60.0, volume=1.0)
    s3 = Shipment(id="S3", weight=20.0, volume=1.0)
    
    # Single vehicle with capacity 100
    # Provide 1 candidate for each using the same vehicle
    c1 = CandidateRoute(shipment_id="S1", vehicle_id="V1", path_min_weight=100.0, path_min_volume=10.0, is_feasible=True, pickup_hub="H1", dropoff_hub="H2", pickup_time=now, dropoff_time=now)
    c2 = CandidateRoute(shipment_id="S2", vehicle_id="V1", path_min_weight=100.0, path_min_volume=10.0, is_feasible=True, pickup_hub="H1", dropoff_hub="H2", pickup_time=now, dropoff_time=now)
    c3 = CandidateRoute(shipment_id="S3", vehicle_id="V1", path_min_weight=100.0, path_min_volume=10.0, is_feasible=True, pickup_hub="H1", dropoff_hub="H2", pickup_time=now, dropoff_time=now)
    
    opt = ORToolsOptimizer(shipments=[s1, s2, s3], all_candidates=[c1, c2, c3])
    result = opt.solve()
    
    assert result.status in ("OPTIMAL", "FEASIBLE")
    assert result.primary is not None
    
    # Should select at most 2 out of 3, because 50+60+20 = 130 > 100
    assert len(result.primary) <= 2
    
    # Specifically, to maximize SLA (shipments), it should select 2 shipments (e.g. 50+20=70 <= 100, or 60+20=80 <= 100)
    assert len(result.primary) == 2
    
def test_no_feasible_piggyback():
    now = datetime.now(timezone.utc)
    s1 = Shipment(id="S1", weight=50.0, volume=1.0)
    
    # All candidates failed constraints
    c1 = CandidateRoute(
        shipment_id="S1", vehicle_id="V1", path_min_weight=100.0, path_min_volume=10.0,
        is_feasible=False, rejection_reason=RejectionReason.DEADLINE_IMPOSSIBLE,
        pickup_hub="H1", dropoff_hub="H2", pickup_time=now, dropoff_time=now
    )
    c2 = CandidateRoute(
        shipment_id="S1", vehicle_id="V2", path_min_weight=100.0, path_min_volume=10.0,
        is_feasible=False, rejection_reason=RejectionReason.INSUFFICIENT_CAPACITY,
        pickup_hub="H1", dropoff_hub="H2", pickup_time=now, dropoff_time=now
    )
    
    opt = ORToolsOptimizer(shipments=[s1], all_candidates=[c1, c2])
    result = opt.solve()
    
    assert result.status == "NO_FEASIBLE_PIGGYBACK"
    assert result.primary is None
    assert result.rejection_breakdown[RejectionReason.DEADLINE_IMPOSSIBLE.value] == 1
    assert result.rejection_breakdown[RejectionReason.INSUFFICIENT_CAPACITY.value] == 1

def test_shadow_plan():
    now = datetime.now(timezone.utc)
    s1 = Shipment(id="S1", weight=50.0, volume=1.0)
    
    # Two identical viable candidates but different vehicles
    # c1 is slightly better on cost
    c1 = CandidateRoute(shipment_id="S1", vehicle_id="V1", path_min_weight=100.0, path_min_volume=10.0, is_feasible=True, incremental_cost=10.0, pickup_hub="H1", dropoff_hub="H2", pickup_time=now, dropoff_time=now)
    c2 = CandidateRoute(shipment_id="S1", vehicle_id="V2", path_min_weight=100.0, path_min_volume=10.0, is_feasible=True, incremental_cost=20.0, pickup_hub="H1", dropoff_hub="H2", pickup_time=now, dropoff_time=now)
    
    opt = ORToolsOptimizer(shipments=[s1], all_candidates=[c1, c2])
    result = opt.solve()
    
    assert result.status in ("OPTIMAL", "FEASIBLE")
    
    # Primary should pick V1
    assert len(result.primary) == 1
    assert result.primary[0].vehicle_id == "V1"
    
    # Shadow should pick V2
    assert result.shadow is not None
    assert len(result.shadow) == 1
    assert result.shadow[0].vehicle_id == "V2"
