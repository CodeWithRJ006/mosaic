from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

class EventType(str, Enum):
    SCENARIO_CREATED = "SCENARIO_CREATED"
    VEHICLE_POSITION_UPDATED = "VEHICLE_POSITION_UPDATED"
    VEHICLE_DELAYED = "VEHICLE_DELAYED"
    VEHICLE_BREAKDOWN = "VEHICLE_BREAKDOWN"
    HUB_CLOSED = "HUB_CLOSED"
    HUB_REOPENED = "HUB_REOPENED"
    CAPACITY_CHANGED = "CAPACITY_CHANGED"
    TRAFFIC_CHANGED = "TRAFFIC_CHANGED"
    SHIPMENT_MISROUTED = "SHIPMENT_MISROUTED"
    SHIPMENT_SCANNED = "SHIPMENT_SCANNED"
    PLAN_CREATED = "PLAN_CREATED"
    PLAN_INVALIDATED = "PLAN_INVALIDATED"
    PLAN_APPROVED = "PLAN_APPROVED"
    PLAN_REJECTED = "PLAN_REJECTED"
    TRANSFER_STARTED = "TRANSFER_STARTED"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"
    SHIPMENT_DELIVERED = "SHIPMENT_DELIVERED"

class EventPayload(BaseModel):
    # Base class for validation. Specific events can have stronger schemas.
    pass

class VehiclePositionUpdated(EventPayload):
    vehicle_id: str
    location: str
    timestamp: datetime

class EventSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any]
    state_version: Optional[int] = None

# Validation dictionary for strict payload checking
EVENT_PAYLOAD_SCHEMAS = {
    EventType.VEHICLE_POSITION_UPDATED: VehiclePositionUpdated,
}

def validate_payload(event_type: EventType, payload: dict):
    if event_type in EVENT_PAYLOAD_SCHEMAS:
        EVENT_PAYLOAD_SCHEMAS[event_type](**payload)
    return True
