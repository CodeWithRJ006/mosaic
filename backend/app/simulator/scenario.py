import random
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from app.models.db import Hub, Vehicle, Shipment

class ScenarioGenerator:
    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)
        self.base_time = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)

    def generate(self) -> Tuple[List[Hub], List[Vehicle], List[Shipment]]:
        hubs = self._generate_hubs()
        vehicles = self._generate_vehicles(hubs)
        shipments = self._generate_shipments(hubs)
        return hubs, vehicles, shipments

    def _generate_hubs(self) -> List[Hub]:
        indian_cities = [
            ("Delhi Gateway", 28.6139, 77.2090),
            ("Mumbai Port Hub", 19.0760, 72.8777),
            ("Bangalore Tech Distribution", 12.9716, 77.5946),
            ("Chennai Harbor Logistics", 13.0827, 80.2707),
            ("Kolkata Eastend Depot", 22.5726, 88.3639),
            ("Hyderabad Central", 17.3850, 78.4867),
            ("Pune Westside Center", 18.5204, 73.8567),
            ("Ahmedabad Express Terminal", 23.0225, 72.5714),
            ("Jaipur North Hub", 26.9124, 75.7873),
            ("Surat Diamond Hub", 21.1702, 72.8311)
        ]
        
        num_hubs = self.rng.randint(6, 9)
        self.rng.shuffle(indian_cities)
        
        hubs = []
        for i in range(num_hubs):
            name, lat, lon = indian_cities[i]
            # Add tiny random jitter so they aren't perfectly identical across seeds
            lat += self.rng.uniform(-0.02, 0.02)
            lon += self.rng.uniform(-0.02, 0.02)
            
            hubs.append(Hub(
                id=f"H{i+1}",
                name=name,
                lat=lat,
                lon=lon
            ))
        return hubs

    def _generate_vehicles(self, hubs: List[Hub]) -> List[Vehicle]:
        num_vehicles = self.rng.randint(25, 35)
        vehicles = []
        hub_ids = [h.id for h in hubs]
        
        for i in range(num_vehicles):
            shift_start = self.base_time + timedelta(hours=self.rng.randint(-2, 2))
            shift_end = shift_start + timedelta(hours=self.rng.randint(8, 12))
            
            # generate schedule
            num_segments = self.rng.randint(3, 6)
            schedule = []
            route = self.rng.choices(hub_ids, k=num_segments+1)
            
            current_time = shift_start
            for j in range(num_segments):
                travel_time = self.rng.randint(20, 90)
                arrival = current_time + timedelta(minutes=travel_time)
                departure = arrival + timedelta(minutes=self.rng.randint(10, 30))
                
                schedule.append({
                    "segment_id": f"V{i+1}_S{j+1}",
                    "from_node": route[j],
                    "to_node": route[j+1],
                    "arrival_time": arrival.isoformat(),
                    "departure_time": departure.isoformat()
                })
                current_time = departure
            
            vehicles.append(Vehicle(
                id=f"V{i+1}",
                max_weight=self.rng.choice([1000.0, 2500.0, 5000.0]),
                max_volume=self.rng.choice([20.0, 40.0, 80.0]),
                current_location=route[0],
                schedule=schedule,
                shift_start=shift_start,
                shift_end=shift_end
            ))
        return vehicles

    def _generate_shipments(self, hubs: List[Hub]) -> List[Shipment]:
        num_shipments = self.rng.randint(150, 250)
        shipments = []
        hub_ids = [h.id for h in hubs]
        
        for i in range(num_shipments):
            origin, destination = self.rng.sample(hub_ids, 2)
            # Intermediate hub
            mid = self.rng.choice([h for h in hub_ids if h not in (origin, destination)])
            
            sla_hours = self.rng.randint(12, 72)
            
            shipments.append(Shipment(
                id=f"S{i+1}",
                weight=self.rng.uniform(1.0, 150.0),
                volume=self.rng.uniform(0.1, 5.0),
                origin=origin,
                destination=destination,
                sla_deadline=self.base_time + timedelta(hours=sla_hours),
                current_location=origin,
                planned_route=[origin, mid, destination],
                status="PLANNED"
            ))
        return shipments
