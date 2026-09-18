import random
from datetime import datetime, timedelta, timezone
from typing import Dict
from backend.app.models.state import Hub, Vehicle, VehicleSegment, Shipment, NetworkState

class ScenarioConfig:
    def __init__(self, seed: int = 58291, vehicles: int = 32, hubs: int = 9, shipments: int = 248, misroute_probability: float = 0.08):
        self.seed = seed
        self.num_vehicles = vehicles
        self.num_hubs = hubs
        self.num_shipments = shipments
        self.misroute_probability = misroute_probability

def generate_scenario(config: ScenarioConfig) -> NetworkState:
    """Generates a complete deterministic world based on the given configuration and seed."""
    random.seed(config.seed)
    
    state = NetworkState(state_version=1)
    
    # 1. Generate Hubs
    for i in range(1, config.num_hubs + 1):
        hub_id = f"H{i}"
        state.hubs[hub_id] = Hub(
            id=hub_id,
            name=f"Hub {i}",
            lat=random.uniform(10.0, 30.0),
            lon=random.uniform(70.0, 90.0)
        )
        
    hub_ids = list(state.hubs.keys())
    
    # Base time for the scenario
    base_time = datetime.now(timezone.utc).replace(hour=16, minute=0, second=0, microsecond=0)
    
    # 2. Generate Vehicles
    for i in range(1, config.num_vehicles + 1):
        v_id = f"V{i}"
        
        # Create a random schedule of 3-5 segments
        num_segments = random.randint(3, 5)
        schedule = []
        current_time = base_time + timedelta(minutes=random.randint(0, 60))
        
        route_hubs = random.sample(hub_ids, num_segments + 1)
        
        for j in range(num_segments):
            travel_time_minutes = random.randint(30, 120)
            arrival = current_time + timedelta(minutes=travel_time_minutes)
            
            schedule.append(VehicleSegment(
                segment_id=f"{v_id}_S{j+1}",
                from_node=route_hubs[j],
                to_node=route_hubs[j+1],
                arrival_time=arrival,
                departure_time=arrival + timedelta(minutes=random.randint(15, 30)) # dwell time
            ))
            current_time = arrival + timedelta(minutes=random.randint(15, 30))
            
        state.vehicles[v_id] = Vehicle(
            id=v_id,
            max_weight=random.choice([500.0, 1000.0, 2000.0]),
            max_volume=random.choice([10.0, 20.0, 40.0]),
            current_location=route_hubs[0],
            schedule=schedule
        )
        
    # 3. Generate Shipments
    for i in range(1, config.num_shipments + 1):
        s_id = f"S{i}"
        origin, destination = random.sample(hub_ids, 2)
        
        # Rough route calculation for simulation purposes
        planned_route = [origin, random.choice([h for h in hub_ids if h not in (origin, destination)]), destination]
        
        state.shipments[s_id] = Shipment(
            id=s_id,
            weight=random.uniform(5.0, 50.0),
            volume=random.uniform(0.1, 1.0),
            origin=origin,
            destination=destination,
            sla_deadline=base_time + timedelta(hours=random.randint(4, 48)),
            current_location=origin,
            planned_route=planned_route,
            status="PLANNED"
        )
        
    return state
