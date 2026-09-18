import os
from typing import List, Dict

def parse_solomon(filepath: str) -> Dict:
    """
    Parses a VRPTW instance in the standard Solomon format.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Benchmark file not found: {filepath}")
        
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        
    name = lines[0]
    
    # Extract vehicle capacity
    vehicle_line = lines[3].split()
    num_vehicles = int(vehicle_line[0])
    capacity = float(vehicle_line[1])
    
    customers = []
    # Data starts after "CUST NO. ..." line
    data_start = 0
    for i, line in enumerate(lines):
        if "CUST NO." in line:
            data_start = i + 1
            break
            
    for i in range(data_start, len(lines)):
        parts = lines[i].split()
        if len(parts) >= 7:
            customers.append({
                "id": int(parts[0]),
                "x": float(parts[1]),
                "y": float(parts[2]),
                "demand": float(parts[3]),
                "ready_time": float(parts[4]),
                "due_date": float(parts[5]),
                "service_time": float(parts[6])
            })
            
    return {
        "name": name,
        "num_vehicles": num_vehicles,
        "capacity": capacity,
        "nodes": customers
    }
