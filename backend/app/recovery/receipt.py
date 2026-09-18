from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from app.recovery.candidates import CandidateRoute
from app.recovery.constraints import RejectionReason
from app.models.db import Shipment

class RejectedCandidateInfo(BaseModel):
    candidate_id: str
    vehicle_id: str
    rejection_reason: str

class DecisionReceipt(BaseModel):
    plan_id: Optional[str] = None
    shipment_id: str
    status: str
    
    # Selected plan info (primary or shadow)
    selected_vehicle_id: Optional[str] = None
    
    # Explicit computed checks surfaced directly from the constraint filter parameters
    weight_check_margin: Optional[float] = None
    time_check_pickup_margin_minutes: Optional[float] = None
    delivery_check_sla_margin_minutes: Optional[float] = None
    downstream_route_check_delay_minutes: Optional[float] = None
    
    rejected_candidates: List[RejectedCandidateInfo] = []
    
    created_at: datetime = datetime.now(timezone.utc)

class ReceiptBuilder:
    @staticmethod
    def build_receipt(
        shipment: Shipment,
        status: str,
        all_candidates: List[CandidateRoute],
        selected_candidate: Optional[CandidateRoute] = None,
        current_time: datetime = datetime.now(timezone.utc)
    ) -> DecisionReceipt:
        
        rejected_info = []
        # Any candidate not feasible, or feasible but not selected, is considered a rejected alternative.
        # But wait, the prompt specifically asks for "rejected_candidates list with each candidate's id and its specific rejection reason"
        # usually meaning those that failed hard constraints.
        for c in all_candidates:
            if not c.is_feasible and c.shipment_id == shipment.id:
                rejected_info.append(RejectedCandidateInfo(
                    candidate_id=c.id,
                    vehicle_id=c.vehicle_id,
                    rejection_reason=c.rejection_reason.value if c.rejection_reason else "UNKNOWN"
                ))
                
        receipt = DecisionReceipt(
            shipment_id=shipment.id,
            status=status,
            rejected_candidates=rejected_info,
            created_at=datetime.now(timezone.utc)
        )
        
        if selected_candidate:
            receipt.selected_vehicle_id = selected_candidate.vehicle_id
            
            # weight check = free path capacity - shipment weight
            receipt.weight_check_margin = selected_candidate.path_min_weight - shipment.weight
            
            # time check = pickup_time - current_time
            if selected_candidate.pickup_time.tzinfo is None:
                pt = selected_candidate.pickup_time.replace(tzinfo=timezone.utc)
            else:
                pt = selected_candidate.pickup_time
            if current_time.tzinfo is None:
                ct = current_time.replace(tzinfo=timezone.utc)
            else:
                ct = current_time
                
            receipt.time_check_pickup_margin_minutes = (pt - ct).total_seconds() / 60.0
            
            # delivery check = sla - dropoff_time
            if shipment.sla_deadline.tzinfo is None:
                sla = shipment.sla_deadline.replace(tzinfo=timezone.utc)
            else:
                sla = shipment.sla_deadline
            if selected_candidate.dropoff_time.tzinfo is None:
                dt = selected_candidate.dropoff_time.replace(tzinfo=timezone.utc)
            else:
                dt = selected_candidate.dropoff_time
                
            receipt.delivery_check_sla_margin_minutes = (sla - dt).total_seconds() / 60.0
            
            # downstream-route check = computed delay to downstream from the candidate
            receipt.downstream_route_check_delay_minutes = selected_candidate.downstream_delay_minutes

        return receipt
