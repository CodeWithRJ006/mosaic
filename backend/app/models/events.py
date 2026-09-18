from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class EventType(str, Enum):
    SCENARIO_CREATED = "SCENARIO_CREATED"
    VEHICLE_DELAYED = "VEHICLE_DELAYED"
    VEHICLE_MOVED = "VEHICLE_MOVED"
    SHIPMENT_MISROUTED = "SHIPMENT_MISROUTED"
    SHIPMENT_MOVED = "SHIPMENT_MOVED"
    PLAN_CREATED = "PLAN_CREATED"
    PLAN_APPROVED = "PLAN_APPROVED"
    PLAN_REJECTED = "PLAN_REJECTED"
    PLAN_INVALIDATED = "PLAN_INVALIDATED"

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any]
    state_version: int # The version this event created
