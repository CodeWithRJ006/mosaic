import pytest
from datetime import datetime, timezone, timedelta
from app.models.db import Shipment
from app.recovery.candidates import CandidateRoute
from app.recovery.constraints import RejectionReason
from app.recovery.receipt import ReceiptBuilder

def test_decision_receipt_computed_values():
    now = datetime.now(timezone.utc)
    
    # 1. Create realistic shipment
    sla = now + timedelta(hours=5)
    shipment = Shipment(
        id="S_TEST",
        weight=25.0,
        volume=2.0,
        sla_deadline=sla
    )
    
    # 2. Create the winning candidate exactly as the solver/filter evaluated it
    pickup = now + timedelta(minutes=45)
    dropoff = now + timedelta(minutes=150) # 2.5 hours
    
    winning_candidate = CandidateRoute(
        id="S_TEST_V_WIN",
        shipment_id="S_TEST",
        vehicle_id="V_WIN",
        pickup_hub="H1",
        dropoff_hub="H2",
        pickup_time=pickup,
        dropoff_time=dropoff,
        path_min_weight=125.0, # Will be checked against 25.0
        path_min_volume=10.0,
        downstream_delay_minutes=12.5,
        is_feasible=True
    )
    
    # 3. Create a rejected candidate
    rejected_candidate = CandidateRoute(
        id="S_TEST_V_REJ",
        shipment_id="S_TEST",
        vehicle_id="V_REJ",
        pickup_hub="H1",
        dropoff_hub="H2",
        pickup_time=now,
        dropoff_time=now,
        path_min_weight=10.0, # Too low
        path_min_volume=10.0,
        is_feasible=False,
        rejection_reason=RejectionReason.INSUFFICIENT_CAPACITY
    )
    
    # 4. Generate receipt
    receipt = ReceiptBuilder.build_receipt(
        shipment=shipment,
        status="OPTIMAL",
        all_candidates=[winning_candidate, rejected_candidate],
        selected_candidate=winning_candidate,
        current_time=now
    )
    
    # 5. Assert equality against computed values
    
    # Weight margin: 125.0 free - 25.0 shipment = 100.0 margin
    assert receipt.weight_check_margin == 100.0
    
    # Time margin (pickup - current): 45 minutes
    assert receipt.time_check_pickup_margin_minutes == 45.0
    
    # SLA margin (SLA - dropoff): 5 hours - 2.5 hours = 150 minutes
    assert receipt.delivery_check_sla_margin_minutes == 150.0
    
    # Downstream delay: straight pass-through
    assert receipt.downstream_route_check_delay_minutes == 12.5
    
    # Check rejection breakdown
    assert len(receipt.rejected_candidates) == 1
    assert receipt.rejected_candidates[0].candidate_id == "S_TEST_V_REJ"
    assert receipt.rejected_candidates[0].rejection_reason == RejectionReason.INSUFFICIENT_CAPACITY.value
