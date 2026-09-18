import pytest
from datetime import datetime, timedelta, timezone
from app.recovery.constraints import HardConstraintFilter, RejectionReason
from app.models.db import Shipment, Vehicle

@pytest.fixture
def base_shipment_vehicle():
    now = datetime.now(timezone.utc)
    s = Shipment(
        id="S1",
        weight=10.0,
        volume=1.0,
        origin="H1",
        destination="H2",
        sla_deadline=now + timedelta(hours=5),
        current_location="H1",
        planned_route=["H1", "H2"],
        status="DELAYED"
    )
    v = Vehicle(
        id="V1",
        max_weight=100.0,
        max_volume=10.0,
        current_location="H1",
        schedule=[],
        shift_start=now - timedelta(hours=1),
        shift_end=now + timedelta(hours=8)
    )
    return s, v, now

def test_constraint_wrong_destination(base_shipment_vehicle):
    s, v, now = base_shipment_vehicle
    # Wrong destination
    feasible, reason = HardConstraintFilter.evaluate(
        shipment=s, vehicle=v, pickup_hub="H1", dropoff_hub="H3",
        pickup_time=now + timedelta(hours=1), dropoff_time=now + timedelta(hours=2),
        current_time=now, path_min_capacity_weight=50.0, path_min_capacity_volume=5.0
    )
    assert not feasible
    assert reason == RejectionReason.WRONG_DESTINATION

def test_constraint_missed_departure(base_shipment_vehicle):
    s, v, now = base_shipment_vehicle
    # Missed departure (pickup_time < current_time)
    feasible, reason = HardConstraintFilter.evaluate(
        shipment=s, vehicle=v, pickup_hub="H1", dropoff_hub="H2",
        pickup_time=now - timedelta(hours=1), dropoff_time=now + timedelta(hours=2),
        current_time=now, path_min_capacity_weight=50.0, path_min_capacity_volume=5.0
    )
    assert not feasible
    assert reason == RejectionReason.MISSED_DEPARTURE

def test_constraint_insufficient_capacity(base_shipment_vehicle):
    s, v, now = base_shipment_vehicle
    # Not enough weight
    feasible, reason = HardConstraintFilter.evaluate(
        shipment=s, vehicle=v, pickup_hub="H1", dropoff_hub="H2",
        pickup_time=now + timedelta(hours=1), dropoff_time=now + timedelta(hours=2),
        current_time=now, path_min_capacity_weight=5.0, path_min_capacity_volume=5.0
    )
    assert not feasible
    assert reason == RejectionReason.INSUFFICIENT_CAPACITY

def test_constraint_deadline_impossible(base_shipment_vehicle):
    s, v, now = base_shipment_vehicle
    # SLA deadline missed
    feasible, reason = HardConstraintFilter.evaluate(
        shipment=s, vehicle=v, pickup_hub="H1", dropoff_hub="H2",
        pickup_time=now + timedelta(hours=1), dropoff_time=now + timedelta(hours=6), # SLA is +5h
        current_time=now, path_min_capacity_weight=50.0, path_min_capacity_volume=5.0
    )
    assert not feasible
    assert reason == RejectionReason.DEADLINE_IMPOSSIBLE

def test_constraint_hub_unavailable(base_shipment_vehicle):
    s, v, now = base_shipment_vehicle
    # Pick up at 3 AM (hub closed)
    pickup = now.replace(hour=3)
    dropoff = pickup + timedelta(hours=2)
    s.sla_deadline = dropoff + timedelta(hours=2)
    current_time = pickup - timedelta(hours=1)
    
    feasible, reason = HardConstraintFilter.evaluate(
        shipment=s, vehicle=v, pickup_hub="H1", dropoff_hub="H2",
        pickup_time=pickup, dropoff_time=dropoff,
        current_time=current_time, path_min_capacity_weight=50.0, path_min_capacity_volume=5.0
    )
    assert not feasible
    assert reason == RejectionReason.HUB_UNAVAILABLE

def test_constraint_transfer_time_impossible(base_shipment_vehicle):
    s, v, now = base_shipment_vehicle
    feasible, reason = HardConstraintFilter.evaluate(
        shipment=s, vehicle=v, pickup_hub="H1", dropoff_hub="H2",
        pickup_time=now + timedelta(hours=1), dropoff_time=now + timedelta(hours=2),
        current_time=now, path_min_capacity_weight=50.0, path_min_capacity_volume=5.0,
        is_transfer=True, transfer_duration_minutes=5.0 # Less than 15 mins
    )
    assert not feasible
    assert reason == RejectionReason.TRANSFER_TIME_IMPOSSIBLE

def test_constraint_downstream_delay_exceeded(base_shipment_vehicle):
    s, v, now = base_shipment_vehicle
    feasible, reason = HardConstraintFilter.evaluate(
        shipment=s, vehicle=v, pickup_hub="H1", dropoff_hub="H2",
        pickup_time=now + timedelta(hours=1), dropoff_time=now + timedelta(hours=2),
        current_time=now, path_min_capacity_weight=50.0, path_min_capacity_volume=5.0,
        downstream_delay_minutes=35.0
    )
    assert not feasible
    assert reason == RejectionReason.DOWNSTREAM_DELAY_EXCEEDED

def test_constraint_pass(base_shipment_vehicle):
    s, v, now = base_shipment_vehicle
    # Avoid 2-4 AM hub closure
    pickup = now.replace(hour=10)
    dropoff = pickup + timedelta(hours=2)
    s.sla_deadline = dropoff + timedelta(hours=2)
    current_time = pickup - timedelta(hours=1)

    feasible, reason = HardConstraintFilter.evaluate(
        shipment=s, vehicle=v, pickup_hub="H1", dropoff_hub="H2",
        pickup_time=pickup, dropoff_time=dropoff,
        current_time=current_time, path_min_capacity_weight=50.0, path_min_capacity_volume=5.0
    )
    assert feasible
    assert reason is None
