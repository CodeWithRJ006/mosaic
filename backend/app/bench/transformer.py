import random
import math
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.db import Hub, Vehicle, Shipment

def create_scenario(db: Session, instance: dict, seed: int, num_shipments_to_disrupt: int = 1):
    """
    Transforms a Solomon VRPTW instance into a MOSAIC network and injects disruptions.
    """
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    
    # 1. Create Hubs
    depot = instance["nodes"][0]
    for node in instance["nodes"]:
        db.add(Hub(
            id=f"HUB_{node['id']}",
            name=f"Node {node['id']}",
            lat=node["y"],
            lon=node["x"]
        ))
        
    # 2. Create Vehicles
    for i in range(instance["num_vehicles"]):
        db.add(Vehicle(
            id=f"VEH_{i}",
            max_weight=instance["capacity"],
            max_volume=instance["capacity"], # assume volume matches weight for bench
            current_location="HUB_0",
            schedule=[], # Will populate some fake schedule below
            shift_start=now,
            shift_end=now + timedelta(hours=24) # generous shift
        ))
        
    db.commit()
    
    # Generate some random schedules to connect the hubs
    # To make recovery interesting, we need vehicles moving between hubs so they can be candidates.
    vehicles = db.query(Vehicle).all()
    for v in vehicles:
        schedule = []
        curr_time = now
        curr_hub = "HUB_0"
        for _ in range(15): # 15 stops
            next_node = rng.choice(instance["nodes"])
            next_hub = f"HUB_{next_node['id']}"
            if next_hub == curr_hub: continue
            
            # distance Euclidean
            dx = depot["x"] - next_node["x"]
            dy = depot["y"] - next_node["y"]
            dist = math.hypot(dx, dy)
            
            arr_time = curr_time + timedelta(minutes=dist)
            dep_time = arr_time + timedelta(minutes=next_node["service_time"])
            
            schedule.append({
                "segment_id": f"{curr_hub}_to_{next_hub}_{rng.randint(1000,9999)}",
                "from_node": curr_hub,
                "to_node": next_hub,
                "arrival_time": arr_time.isoformat(),
                "departure_time": dep_time.isoformat(),
                "distance": dist
            })
            curr_time = dep_time
            curr_hub = next_hub
            
        v.schedule = schedule
    
    # 3. Create Shipments (Customers)
    shipments = []
    for node in instance["nodes"][1:]: # Skip depot
        sla_mins = node["due_date"]
        sla = now + timedelta(minutes=sla_mins)
        
        s = Shipment(
            id=f"SHP_{node['id']}",
            weight=node["demand"],
            volume=node["demand"],
            origin="HUB_0",
            destination=f"HUB_{node['id']}",
            current_location="HUB_0",
            sla_deadline=sla,
            planned_route=[],
            status="PLANNED"
        )
        db.add(s)
        shipments.append(s)
        
    db.commit()
    
    # 4. Inject Disruptions
    disrupted_shipments = []
    for _ in range(num_shipments_to_disrupt):
        s = rng.choice(shipments)
        # Misroute to a random hub that is not origin or destination
        wrong_node = rng.choice([n for n in instance["nodes"] if n["id"] not in (0, int(s.id.split('_')[1]))])
        s.current_location = f"HUB_{wrong_node['id']}"
        s.status = "MISROUTED"
        disrupted_shipments.append(s.id)
        
    db.commit()
    return disrupted_shipments
