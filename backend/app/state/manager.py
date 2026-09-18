from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.db import Event, Vehicle, Shipment
from app.models.events import EventType, validate_payload, EventSchema
from app.api.ws import manager
import asyncio
import uuid

class StateManager:
    def __init__(self, db_session: Session):
        self.db = db_session
        self._load_version()

    def _load_version(self):
        max_v = self.db.query(func.max(Event.state_version)).scalar()
        self.current_version = max_v if max_v is not None else 0

    async def dispatch(self, event_type: EventType, payload: dict) -> Event:
        # 1. Validation
        try:
            validate_payload(event_type, payload)
        except Exception as e:
            raise ValueError(f"Malformed event payload: {e}")

        # 2. Increment version
        self.current_version += 1
        new_version = self.current_version
        
        # 3. Create Event ORM object
        event_schema = EventSchema(
            id=str(uuid.uuid4()),
            type=event_type,
            payload=payload,
            state_version=new_version
        )
        
        db_event = Event(
            id=event_schema.id,
            type=event_schema.type.value,
            timestamp=event_schema.timestamp,
            payload=event_schema.payload,
            state_version=event_schema.state_version
        )
        
        # 4. Apply Projection Mutations
        cascaded_events = []
        self._apply_projection(db_event, cascaded_events)
        
        # 5. Persist
        self.db.add(db_event)
        self.db.commit()
        
        # 6. Broadcast
        await manager.broadcast_event({
            "type": "STATE_UPDATED",
            "state_version": new_version,
            "payload": {
                "event_id": db_event.id,
                "event_type": db_event.type,
                "event_payload": db_event.payload
            }
        })
        
        # 7. Dispatch cascaded events sequentially
        for c_type, c_payload in cascaded_events:
            await self.dispatch(c_type, c_payload)
            
        return db_event

    def _apply_projection(self, event: Event, cascaded_events: list):
        if event.type == EventType.VEHICLE_POSITION_UPDATED.value:
            v_id = event.payload.get("vehicle_id")
            new_loc = event.payload.get("location")
            if v_id and new_loc:
                vehicle = self.db.query(Vehicle).filter(Vehicle.id == v_id).first()
                if vehicle:
                    vehicle.current_location = new_loc
                    
        # Check staleness if it's a mutating physical event
        if event.type in [
            EventType.VEHICLE_POSITION_UPDATED.value,
            EventType.VEHICLE_DELAYED.value,
            EventType.VEHICLE_BREAKDOWN.value,
            EventType.HUB_CLOSED.value,
            EventType.HUB_REOPENED.value,
            EventType.CAPACITY_CHANGED.value
        ]:
            from app.recovery.lifecycle import PlanLifecycle
            lifecycle = PlanLifecycle(self.db, self.current_version, cascaded_events)
            lifecycle.check_staleness(event)
