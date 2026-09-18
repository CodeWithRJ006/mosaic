import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.db import Vehicle
from app.models.events import EventType
from app.state.manager import StateManager

class SimulationEngine:
    def __init__(self, get_db_session_factory, time_scale: float = 1.0):
        # time_scale = 1.0 -> 1 sim sec = 1 wall sec
        # time_scale = 60.0 -> 60 sim sec = 1 wall sec
        self.time_scale = time_scale
        self.get_db = get_db_session_factory
        self.is_running = False
        
        # Determine the initial simulation time (find minimum shift_start among vehicles, or just use current utc)
        self.current_sim_time = None

    def initialize_time(self):
        with self.get_db() as db:
            first_vehicle = db.query(Vehicle).order_by(Vehicle.shift_start.asc()).first()
            if first_vehicle and first_vehicle.shift_start:
                self.current_sim_time = first_vehicle.shift_start
                if self.current_sim_time.tzinfo is None:
                    self.current_sim_time = self.current_sim_time.replace(tzinfo=timezone.utc)
            else:
                self.current_sim_time = datetime.now(timezone.utc)

    async def tick(self, delta_sim_seconds: float):
        if not self.current_sim_time:
            self.initialize_time()
            
        self.current_sim_time += timedelta(seconds=delta_sim_seconds)
        
        with self.get_db() as db:
            manager = StateManager(db)
            vehicles = db.query(Vehicle).all()
            
            for v in vehicles:
                # Basic logic to advance vehicle position along route based on schedule
                for segment in v.schedule:
                    arr = datetime.fromisoformat(segment["arrival_time"])
                    if arr.tzinfo is None: arr = arr.replace(tzinfo=timezone.utc)
                    dep = datetime.fromisoformat(segment["departure_time"])
                    if dep.tzinfo is None: dep = dep.replace(tzinfo=timezone.utc)
                    
                    # If we just arrived at a node in this tick
                    if arr <= self.current_sim_time <= dep and v.current_location != segment["to_node"]:
                        await manager.dispatch(
                            EventType.VEHICLE_POSITION_UPDATED, 
                            {
                                "vehicle_id": v.id,
                                "location": segment["to_node"],
                                "timestamp": self.current_sim_time.isoformat()
                            }
                        )
                        break

    async def loop(self, tick_wall_seconds: float = 1.0):
        self.is_running = True
        self.initialize_time()
        while self.is_running:
            await self.tick(tick_wall_seconds * self.time_scale)
            await asyncio.sleep(tick_wall_seconds)

    def stop(self):
        self.is_running = False
