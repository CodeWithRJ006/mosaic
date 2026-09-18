from enum import Enum
from typing import Tuple, Optional
from datetime import datetime, timedelta, timezone
from app.models.db import Shipment, Vehicle

class RejectionReason(str, Enum):
    INSUFFICIENT_CAPACITY = "INSUFFICIENT_CAPACITY"
    WRONG_DESTINATION = "WRONG_DESTINATION"
    MISSED_DEPARTURE = "MISSED_DEPARTURE"
    DEADLINE_IMPOSSIBLE = "DEADLINE_IMPOSSIBLE"
    HUB_UNAVAILABLE = "HUB_UNAVAILABLE"
    TRANSFER_TIME_IMPOSSIBLE = "TRANSFER_TIME_IMPOSSIBLE"
    DOWNSTREAM_DELAY_EXCEEDED = "DOWNSTREAM_DELAY_EXCEEDED"

class HardConstraintFilter:
    @staticmethod
    def evaluate(
        shipment: Shipment,
        vehicle: Vehicle,
        pickup_hub: str,
        dropoff_hub: str,
        pickup_time: datetime,
        dropoff_time: datetime,
        current_time: datetime,
        path_min_capacity_weight: float,
        path_min_capacity_volume: float,
        is_transfer: bool = False,
        transfer_duration_minutes: float = 0.0,
        downstream_delay_minutes: float = 0.0
    ) -> Tuple[bool, Optional[RejectionReason]]:
        
        # 1. Geography Reachability / Route
        if dropoff_hub != shipment.destination and not is_transfer:
            return False, RejectionReason.WRONG_DESTINATION
            
        # 2. Time Feasibility (Missed Departure)
        if pickup_time < current_time:
            return False, RejectionReason.MISSED_DEPARTURE
            
        # 3. Capacity
        if path_min_capacity_weight < shipment.weight or path_min_capacity_volume < shipment.volume:
            return False, RejectionReason.INSUFFICIENT_CAPACITY
            
        # 4. Deadline Impossible
        sla = shipment.sla_deadline
        if sla.tzinfo is None: sla = sla.replace(tzinfo=timezone.utc)
        if dropoff_time > sla:
            return False, RejectionReason.DEADLINE_IMPOSSIBLE
            
        # 5. Hub Operational Window (mock logic: hubs closed between 2AM and 4AM)
        if 2 <= pickup_time.hour < 4 or 2 <= dropoff_time.hour < 4:
            return False, RejectionReason.HUB_UNAVAILABLE
            
        # 6. Transfer time impossible (if applicable)
        if is_transfer and transfer_duration_minutes < 15.0:
            return False, RejectionReason.TRANSFER_TIME_IMPOSSIBLE
            
        # 7. Downstream delay check
        # e.g., if inserting this shipment delays the vehicle > 30 mins, it might break other SLAs
        if downstream_delay_minutes > 30.0:
            return False, RejectionReason.DOWNSTREAM_DELAY_EXCEEDED
            
        return True, None
